import asyncio
import logging
import os

from PySide6.QtCore import QThread, Signal, QObject

from app.config import ConfigManager
from core import (
    SkanlatorEngine, CaptureRegion, Language,
    RapidOcrService, MssScreenCaptureService, LlamaCppTranslation, ServiceStatus
)

logger = logging.getLogger(__name__)


class EngineWorker(QThread):
    # Signals emitted from background asyncio loop thread back to main thread
    scan_success = Signal(object)  # Emits ScanSuccessEvent
    screen_updated = Signal(object)  # Emits ScreenUpdatedEvent
    status_changed = Signal(dict)  # Emits worker status changes

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.loop = None
        self.engine = None
        self._region = None

    def run(self):
        """Thread entry point running the asyncio event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.status_changed.emit({"status": "initializing"})

        try:
            # Resolve absolute paths for models
            det_path = os.path.abspath(self.config_manager.get("ocr_det_model_path"))
            cls_path = os.path.abspath(self.config_manager.get("ocr_cls_model_path"))
            rec_path = os.path.abspath(self.config_manager.get("ocr_rec_model_path"))

            from app.files import get_models_dir
            model_root = get_models_dir()

            # Create service instances
            ocr_service = RapidOcrService(
                model_root_dir=model_root,
                det_model_path=det_path,
                cls_model_path=cls_path,
                rec_model_path=rec_path
            )

            translation_service = LlamaCppTranslation(
                model_path=os.path.abspath(self.config_manager.get("translate_model_path")),
                prompt_template=self.config_manager.get("translate_system_prompt"),
                n_ctx=self.config_manager.get("translate_n_ctx"),
                temperature=self.config_manager.get("translate_temperature"),
                top_p=self.config_manager.get("translate_top_p"),
                max_tokens=self.config_manager.get("translate_max_tokens")
            )

            capture_service = MssScreenCaptureService(
                capture_interval=self.config_manager.get("capture_interval"),
                sensitivity=self.config_manager.get("capture_sensitivity"),
                monitor_index=self.config_manager.get("capture_monitor")
            )

            # Create core engine
            self.engine = SkanlatorEngine.create(
                ocr_service=ocr_service,
                translation_service=translation_service,
                capture_service=capture_service,
                src_lang=Language.EN,
                dest_lang=Language.VI
            )

            # Warm up models
            self.loop.call_soon_threadsafe(self.engine.initialize)
            self.loop.create_task(self._monitor_initialization())

            # Connect callbacks
            self.engine.on_screen_updated(self._handle_screen_updated)
            self.engine.on_scan_success(self._handle_scan_success)

            # Start event loop
            self.loop.run_forever()

        except Exception as e:
            logger.error(f"Error in engine worker loop: {e}", exc_info=True)
            self.status_changed.emit({"status": "error", "message": str(e)})
        finally:
            if self.loop:
                self.loop.close()
                self.loop = None

    async def _monitor_initialization(self):
        while True:
            if not self.engine:
                await asyncio.sleep(0.1)
                continue

            statuses = self.engine.get_services_status()
            self.status_changed.emit({"status": "services_status", "services": statuses})

            # Exit loop if all services are initialized (ready or error)
            if all(s in (ServiceStatus.READY, ServiceStatus.ERROR) for s in statuses.values()):
                break

            await asyncio.sleep(0.5)

    async def _handle_screen_updated(self, event):
        self.screen_updated.emit(event)

    async def _handle_scan_success(self, event):
        self.scan_success.emit(event)

    def start_engine(self, region: CaptureRegion):
        if self.loop and self.engine:
            self._region = region
            asyncio.run_coroutine_threadsafe(self._start_engine_coro(), self.loop)

    async def _start_engine_coro(self):
        try:
            if self.engine:
                await self.engine.start(self._region)
                self.status_changed.emit({"status": "running"})
        except Exception as e:
            logger.error(f"Failed to start engine: {e}", exc_info=True)
            self.status_changed.emit({"status": "error", "message": f"Start Error: {e}"})

    def stop_engine(self):
        if self.loop and self.engine:
            asyncio.run_coroutine_threadsafe(self._stop_engine_coro(), self.loop)

    async def _stop_engine_coro(self):
        try:
            if self.engine:
                await self.engine.stop()
                self.status_changed.emit({"status": "stopped"})
        except Exception as e:
            logger.error(f"Failed to stop engine: {e}", exc_info=True)
            self.status_changed.emit({"status": "error", "message": f"Stop Error: {e}"})

    def stop_worker(self):
        """Cleanly destroys the engine, stops the loop, and exits the thread."""
        if self.loop:
            # First, destroy the engine
            future = asyncio.run_coroutine_threadsafe(self._destroy_engine_coro(), self.loop)
            try:
                future.result(timeout=5.0)
            except Exception as e:
                logger.error(f"Error destroying engine during worker stop: {e}", exc_info=True)

            # Then, stop loop
            self.loop.call_soon_threadsafe(self.loop.stop)

        self.wait()  # Block caller thread until QThread finishes

    async def _destroy_engine_coro(self):
        if self.engine:
            try:
                await self.engine.destroy()
            finally:
                self.engine = None


class SkanlatorController(QObject):
    # Proxy signals so UI can subscribe once
    scan_success = Signal(object)
    screen_updated = Signal(object)
    status_changed = Signal(dict)

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.worker = None

    def initialize_engine(self):
        """Create and start the engine worker thread."""
        if self.worker is not None:
            return

        self.worker = EngineWorker(self.config_manager)
        self.worker.scan_success.connect(self.scan_success.emit)
        self.worker.screen_updated.connect(self.screen_updated.emit)
        self.worker.status_changed.connect(self.status_changed.emit)
        self.worker.start()

    def start_scanning(self, region: CaptureRegion):
        if self.worker:
            self.worker.start_engine(region)

    def stop_scanning(self):
        if self.worker:
            self.worker.stop_engine()

    def handle_settings_changed(self):
        """Destroy the old engine / worker and re-initialize to apply new settings."""
        logger.info("Settings changed. Reinitializing engine...")
        self.destroy_engine()
        self.initialize_engine()

    def destroy_engine(self):
        """Shut down the worker thread and wait for complete engine destruction."""
        if self.worker:
            self.worker.stop_worker()
            self.worker = None
