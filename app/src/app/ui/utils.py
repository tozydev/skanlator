import logging
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


def prevent_screen_capture(widget) -> None:
    """
    Sets the window display affinity to exclude the window from screen capture on Windows,
    preventing feedback loops while keeping the window fully visible to the user.
    """
    if os.name == 'nt':
        try:
            import ctypes
            hwnd = int(widget.winId())
            # 17 is WDA_EXCLUDEFROMCAPTURE
            # noinspection PyUnresolvedReferences
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 17)
        except Exception as e:
            logger.warning(f"Could not set window display affinity for {widget.__class__.__name__}: {e}")


def set_app_icon(app: QWidget, asset_name: str):
    """
    Sets the application icon for the given QWidget (typically the main window).
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # noinspection PyProtectedMember
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.join(os.getcwd(), "assets"))

    icon_path = os.path.join(base_path, asset_name)

    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
