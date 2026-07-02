import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Any, Dict, List

import numpy as np

from .services import OcrService, TranslationService, ScreenCaptureService, CaptureRegion, ScreenUpdatedEvent, Language

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScanResult:
    id: str
    box: np.ndarray
    original_text: str
    translated_text: str
    score: float


@dataclass(frozen=True)
class ScanSuccessEvent:
    results: List[ScanResult]
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SkanlatorEngine(ABC):
    @staticmethod
    def create(
            ocr_service: OcrService,
            translation_service: TranslationService,
            capture_service: ScreenCaptureService,
            src_lang: Language = Language.EN,
            dest_lang: Language = Language.VI,
    ) -> "SkanlatorEngine":
        """Factory method to create the concrete engine implementation."""
        from .internal.engine import SkanlatorEngineImpl
        return SkanlatorEngineImpl(
            ocr_service=ocr_service,
            translation_service=translation_service,
            capture_service=capture_service,
            src_lang=src_lang,
            dest_lang=dest_lang,
        )

    @abstractmethod
    def initialize(self) -> None:
        """Initialize and warm up the OCR and translation services."""
        pass

    @abstractmethod
    async def destroy(self) -> None:
        """Clean up resources and stop any running tasks."""
        pass

    @abstractmethod
    async def start(self, region: CaptureRegion) -> None:
        """Start the engine's asynchronous capture loop and listeners."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the engine's asynchronous capture loop and listeners."""
        pass

    @abstractmethod
    def on_screen_updated(self, callback: Callable[[ScreenUpdatedEvent], Awaitable[None]]) -> None:
        """Register a callback to be notified when the screen is updated (e.g., to clear overlays)."""
        pass

    @abstractmethod
    def on_scan_success(self, callback: Callable[[ScanSuccessEvent], Awaitable[None]]) -> None:
        """Register a callback to be notified when scan results are ready (e.g., to draw overlays)."""
        pass

    @abstractmethod
    def get_services_status(self) -> Dict[str, Any]:
        """Get a dictionary with the status of each service."""
        pass
