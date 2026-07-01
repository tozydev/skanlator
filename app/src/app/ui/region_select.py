from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QGuiApplication
from PySide6.QtWidgets import QDialog

from app.config import ConfigManager


class RegionSelector(QDialog):
    def __init__(self, config_manager: ConfigManager, outline_color_hex: str):
        # Pass parent=None to ensure it is treated as a top-level window,
        # preventing it from being constrained by the parent toolbar window.
        super().__init__(None)
        self.config_manager = config_manager
        self.outline_color_hex = outline_color_hex
        self.start_pos = None  # Stored in global coordinates
        self.current_pos = None  # Stored in global coordinates
        self.selected_region = None  # Stored in global coordinates
        self._init_ui()

    def _init_ui(self):
        # Frameless, translucent, stays on top, Dialog style
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Determine target screen based on config
        screens = QGuiApplication.screens()
        monitor_idx = 0
        if self.config_manager is not None:
            monitor_idx = (self.config_manager.get("capture_monitor") or 1) - 1

        if 0 <= monitor_idx < len(screens):
            screen = screens[monitor_idx]
        else:
            screen = QGuiApplication.primaryScreen()

        if screen:
            # Force creation of window handle and associate with target screen
            self.createWinId()
            window_handle = self.windowHandle()
            if window_handle:
                window_handle.setScreen(screen)
            # Position at target screen's bounds
            self.setGeometry(screen.geometry())

        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        overlay_color = QColor(0, 0, 0, 110)  # ~43% dark opacity overlay

        if self.start_pos and self.current_pos:
            # Map global coordinates to local coordinates of this overlay widget for painting
            local_start = self.mapFromGlobal(self.start_pos)
            local_current = self.mapFromGlobal(self.current_pos)
            rect = QRect(local_start, local_current).normalized()

            # Cutout: Draw overlay everywhere except the selected region
            path = QPainterPath()
            path.addRect(QRect(self.rect()))
            path.addRect(rect)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(overlay_color)
            painter.drawPath(path)

            # Draw region selection border
            pen = QPen(QColor(self.outline_color_hex), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
        else:
            # Full overlay
            painter.fillRect(self.rect(), overlay_color)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Use global coordinates to support multi-monitor arrangements correctly
            self.start_pos = event.globalPosition().toPoint()
            self.current_pos = self.start_pos
            self.update()

    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.current_pos = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.start_pos:
            self.current_pos = event.globalPosition().toPoint()

            # Calculate rect in global coordinates
            rect = QRect(self.start_pos, self.current_pos).normalized()
            if rect.width() > 8 and rect.height() > 8:
                self.selected_region = [rect.x(), rect.y(), rect.width(), rect.height()]

            self.start_pos = None
            self.current_pos = None
            self.accept()

    def keyPressEvent(self, event):
        # Escape cancels the selection
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
