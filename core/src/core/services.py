import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Callable, Awaitable
from enum import auto

import numpy as np


class ServiceStatus(Enum):
    IDLE = auto()
    INITIALIZING = auto()
    READY = auto()
    ERROR = auto()


class Language(Enum):
    VI = "Vietnamese"
    EN = "English"


@dataclass(frozen=True)
class CaptureRegion:
    top: int
    left: int
    width: int
    height: int


@dataclass(frozen=True)
class ScreenUpdatedEvent:
    image: np.ndarray
    timestamp: float = field(default_factory=time.time)


class ScreenCaptureService(ABC):
    status: ServiceStatus = ServiceStatus.IDLE

    @abstractmethod
    async def start(self, region: CaptureRegion) -> None:
        """Start the screen capture service."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the screen capture service."""
        pass

    @abstractmethod
    def on_screen_changed(self, callback: Callable[[ScreenUpdatedEvent], Awaitable[None]]) -> None:
        """Register a callback to be notified when a new screen frame with visual changes is captured."""
        pass


@dataclass(frozen=True)
class OcrResult:
    id: str
    box: np.ndarray
    text: str
    confidence: float


class OcrService(ABC):
    status: ServiceStatus = ServiceStatus.IDLE

    @abstractmethod
    def initialize(self) -> None:
        """Perform initialization and warm-up of the OCR models if necessary."""
        pass

    @abstractmethod
    def detect(self, image: np.ndarray) -> List[OcrResult]:
        """Perform text detection and recognition."""
        pass

    @abstractmethod
    def destroy(self) -> None:
        """Destroy the service and release all resources."""
        pass


@dataclass(frozen=True)
class TranslationResult:
    success: bool
    translations: dict[str, str]  # maps OcrResult.id to translated_text


class TranslationService(ABC):
    status: ServiceStatus = ServiceStatus.IDLE

    @abstractmethod
    def initialize(self) -> None:
        """Perform initialization and warm-up of the translation models if necessary."""
        pass

    @abstractmethod
    def translate(self, regions: List[OcrResult], src: Language, dest: Language) -> TranslationResult:
        """Translate a list of OCR results, preserving their boxes and IDs.
        Returns a TranslationResult containing success status and translated texts mapped by OCR result ID.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """Destroy the service and release all resources."""
        pass
