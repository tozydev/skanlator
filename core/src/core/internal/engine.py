import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Awaitable, Optional

from ..engine import SkanlatorEngine, CaptureRegion, ScanSuccessEvent, ScanResult
from ..services import OcrService, TranslationService, ScreenCaptureService, ScreenUpdatedEvent, Language, ServiceStatus
from ..utils.event_bus import EventBus

logger = logging.getLogger(__name__)


class SkanlatorEngineImpl(SkanlatorEngine):
    def __init__(
            self,
            ocr_service: OcrService,
            translation_service: TranslationService,
            capture_service: ScreenCaptureService,
            src_lang: Language,
            dest_lang: Language,
    ) -> None:
        self.ocr_service = ocr_service
        self.translation_service = translation_service
        self.capture_service = capture_service
        self.src_lang = src_lang
        self.dest_lang = dest_lang

        self._event_bus = EventBus()

        self._executor = ThreadPoolExecutor(max_workers=1)

        self._active_task: Optional[asyncio.Task[None]] = None
        self._init_task: Optional[asyncio.Task[None]] = None
        self._is_running = False
        self._is_destroyed = False

    def initialize(self) -> None:
        self._ensure_not_destroyed()
        if self._init_task and not self._init_task.done():
            return

        self._init_task = asyncio.create_task(self._initialize_services())
        self.capture_service.on_screen_changed(self._handle_screen_updated)

    def _ensure_not_destroyed(self):
        if self._is_destroyed:
            raise RuntimeError("SkanlatorEngine has been destroyed and cannot be used.")

    def get_services_status(self) -> dict[str, ServiceStatus]:
        return {
            "ocr": self.ocr_service.status,
            "translation": self.translation_service.status,
        }

    async def _initialize_services(self) -> None:
        try:
            logger.debug("Starting service warm-up for OCR and Translation services.")
            ocr_task = asyncio.create_task(self._run_service(self.ocr_service.initialize))
            translation_task = asyncio.create_task(self._run_service(self.translation_service.initialize))

            await asyncio.gather(ocr_task, translation_task, return_exceptions=True)

            logger.info(f"OCR service initialized with status: {self.ocr_service.status}")
            logger.info(f"Translation service initialized with status: {self.translation_service.status}")

        except* asyncio.CancelledError:
            pass
        except* Exception as e:
            logger.error(f"Error during service warm-up: {e}", exc_info=True)

    async def _handle_screen_updated(self, event: ScreenUpdatedEvent) -> None:
        # Cancel the previous active processing task to avoid wasting resources on obsolete frames
        await self._cancel_task(self._active_task)

        # Spawn a new task to process the current frame
        self._active_task = asyncio.create_task(self._process_frame(event))

    async def _process_frame(self, event: ScreenUpdatedEvent) -> None:
        await self._wait_for_initialized()
        try:
            # 1. OCR Step
            ocr_results = await self._run_service(self.ocr_service.detect, event.image)
            if not ocr_results:
                return

            # 2. Translation Step
            translation_result = await self._run_service(
                self.translation_service.translate,
                ocr_results,
                src=self.src_lang,
                dest=self.dest_lang
            )

            # 3. Compile Results
            scan_results = []
            for res in ocr_results:
                translated_text = translation_result.translations.get(res.id, "")
                scan_results.append(
                    ScanResult(
                        id=res.id,
                        box=res.box,
                        original_text=res.text,
                        translated_text=translated_text,
                        score=res.confidence,
                    )
                )

            # 4. Publish Success only if there is data
            if scan_results:
                await self._event_bus.publish(ScanSuccessEvent(results=scan_results))

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error processing frame: {e}", exc_info=True)

    async def _wait_for_initialized(self):
        if self._init_task:
            await self._init_task

    async def destroy(self) -> None:
        if self._is_destroyed:
            return

        self._is_destroyed = True

        await self.stop()

        await self._cancel_task(self._active_task, wait=True)
        self._init_task = None

        # Destroy services
        if self.ocr_service:
            await self._run_service(self.ocr_service.destroy)
        if self.translation_service:
            await self._run_service(self.translation_service.destroy)

        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

        logger.info("SkanlatorEngine destroyed and resources cleaned up.")

    async def start(self, region: CaptureRegion) -> None:
        self._ensure_not_destroyed()
        if self._is_running:
            return

        self._is_running = True
        await self._wait_for_initialized()

        await self.capture_service.start(region)

    async def stop(self) -> None:
        if not self._is_running:
            return

        self._is_running = False

        # Stop capture service
        await self.capture_service.stop()

        await self._cancel_task(self._active_task, wait=True)
        self._active_task = None

    def on_screen_updated(self, callback: Callable[[ScreenUpdatedEvent], Awaitable[None]]) -> None:
        self.capture_service.on_screen_changed(callback)

    def on_scan_success(self, callback: Callable[[ScanSuccessEvent], Awaitable[None]]) -> None:
        self._event_bus.subscribe(ScanSuccessEvent, callback)

    async def _run_service(self, func, *args, **kwargs):
        import inspect
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))

    @staticmethod
    async def _cancel_task(task: Optional[asyncio.Task[None]], wait=False):
        if task and not task.done():
            task.cancel()
            if wait:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
