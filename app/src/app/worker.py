import logging

from PySide6.QtCore import Signal, QObject

from app.config import ConfigManager
from core import (
    CaptureRegion
)

logger = logging.getLogger(__name__)


class SkanlatorController(QObject):
    # Proxy signals so UI can subscribe once
    scan_success = Signal(object)
    screen_updated = Signal(object)
    status_changed = Signal(str)

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager

    def initialize_engine(self):
        pass

    def start_scanning(self, region: CaptureRegion):
        pass

    def stop_scanning(self):
        pass

    def handle_settings_changed(self):
        pass

    def destroy_engine(self):
        pass
