import logging
import os

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
