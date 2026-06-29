import asyncio
import logging
import time
from typing import Callable, Awaitable, Optional

import imagehash
import numpy as np
from PIL import Image
from mss import MSS

from ..utils import EventBus
from ..services import ScreenCaptureService, CaptureRegion, ScreenUpdatedEvent

logger = logging.getLogger(__name__)


class MssScreenCaptureService(ScreenCaptureService):
    """
    High-performance asynchronous screen capture service using mss and imagehash.
    Optimized to bypass intermediate PIL-to-NumPy conversions, keeping the emitted
    frame in its raw, native BGRA format.
    """

    def __init__(self, capture_interval: float = 0.2, sensitivity: float = 1.0, monitor_index: int = 1) -> None:
        self.capture_interval = capture_interval
        self.sensitivity = sensitivity
        self.monitor_index = monitor_index

        self._region: Optional[CaptureRegion] = None

        self._event_bus = EventBus()

        self._is_running = False
        self._capture_task: Optional[asyncio.Task[None]] = None
        self._prev_frame: Optional[np.ndarray] = None
        self._prev_hash: Optional[imagehash.ImageHash] = None

    def on_screen_changed(self, callback: Callable[[ScreenUpdatedEvent], Awaitable[None]]) -> None:
        self._event_bus.subscribe(ScreenUpdatedEvent, callback)

    async def start(self, region: CaptureRegion) -> None:
        if self._is_running:
            logger.warning("ScreenCaptureService is already running.")
            return

        self._region = region
        self._is_running = True
        self._prev_frame = None
        self._prev_hash = None

        # Start the capture loop in the background
        self._capture_task = asyncio.create_task(self._capture_loop())
        logger.info(f"ScreenCaptureService started on monitor index {self.monitor_index}.")

    async def stop(self) -> None:
        if not self._is_running:
            return

        self._is_running = False
        if self._capture_task:
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
            self._capture_task = None

        self._prev_frame = None
        self._prev_hash = None
        logger.info("ScreenCaptureService stopped successfully.")

    async def _capture_loop(self) -> None:
        # Map sensitivity to a Hamming distance threshold for 64-bit dhash
        if self.sensitivity <= 0:
            threshold = 64  # Ignores all changes
        else:
            threshold = max(0, int(8 / self.sensitivity))

        loop = asyncio.get_running_loop()

        with MSS() as sct:
            if self.monitor_index >= len(sct.monitors):
                logger.error(
                    f"Selected monitor index {self.monitor_index} is out of bounds. "
                    f"Available: {len(sct.monitors) - 1} monitor(s)."
                )
                self._is_running = False
                return

            monitor_info = sct.monitors[self.monitor_index]

            while self._is_running:
                start_time = time.monotonic()
                try:
                    if not self._region:
                        await asyncio.sleep(self.capture_interval)
                        continue

                    # Construct target boundary relative to the chosen monitor's position
                    monitor = {
                        "top": monitor_info["top"] + self._region.top,
                        "left": monitor_info["left"] + self._region.left,
                        "width": self._region.width,
                        "height": self._region.height,
                    }

                    # Low-latency screen grab via OS graphics API
                    sct_img = sct.grab(monitor)

                    # Execute CPU-heavy hashing & array extraction in a separate thread
                    frame_np, current_hash = await loop.run_in_executor(
                        None, self._process_frame_sync, sct_img
                    )

                    should_notify = False
                    if self._prev_hash is None:
                        should_notify = True
                    else:
                        hash_distance = current_hash - self._prev_hash
                        if hash_distance > threshold:
                            logger.debug(
                                f"Visual change detected. Hash distance: {hash_distance} "
                                f"(Threshold: {threshold})"
                            )
                            should_notify = True

                    self._prev_frame = frame_np
                    self._prev_hash = current_hash

                    # Concurrently dispatch events to registered callbacks
                    if should_notify:
                        event = ScreenUpdatedEvent(image=frame_np, timestamp=time.time())
                        await self._event_bus.publish(event)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.exception("An error occurred during the screen capture loop cycle: %s", e)

                # Calculate remaining loop delay precisely to prevent drift
                elapsed = time.monotonic() - start_time
                delay = max(0.001, self.capture_interval - elapsed)
                await asyncio.sleep(delay)

    @staticmethod
    def _process_frame_sync(sct_img) -> tuple[np.ndarray, imagehash.ImageHash]:
        """
        Processes a raw mss image synchronous-bound chunk.

        By directly mapping the mss C-buffer to a NumPy array, we preserve the
        native BGRA format and eliminate the main CPU bottleneck.
        """
        # 1. Directly convert the MSS screenshot to a NumPy array.
        # This is extremely fast because it wraps the native OS BGRA graphics memory buffer.
        frame_np = np.array(sct_img)

        # 2. Only convert to PIL to generate the difference hash.
        # Crucially, we NEVER convert this PIL image back to NumPy, saving massive CPU cycles.
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        h = imagehash.dhash(img)

        return frame_np, h
