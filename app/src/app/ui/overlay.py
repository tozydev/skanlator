import math
import os
from typing import cast

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFontDatabase, QFont, QPolygonF
from PySide6.QtWidgets import QWidget

from app.config import ConfigManager
from .utils import prevent_screen_capture


class OverlayRegion(QWidget):
    def __init__(self, rect_coords, config_manager: ConfigManager, outline_color_hex: str, outline_width: int):
        super().__init__()
        self.rect_coords = rect_coords  # [x, y, w, h] in global coordinates
        self.config_manager = config_manager
        self.outline_color_hex = outline_color_hex
        self.outline_width = outline_width
        self.scan_results = []
        self._init_ui()

    def _init_ui(self):
        # Completely click-through, frameless, stays on top, tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Position with padding corresponding to outline width to prevent clipping
        x, y, w, h = self.rect_coords
        pad = self.outline_width
        self.setGeometry(x - pad, y - pad, w + (pad * 2), h + (pad * 2))

        # Exclude overlay window from screen capture on Windows to prevent feedback loops
        prevent_screen_capture(self)

    def update_style(self, outline_color_hex, outline_width):
        self.outline_color_hex = outline_color_hex
        self.outline_width = outline_width

        # Recalculate geometry bounds in case width changed
        x, y, w, h = self.rect_coords
        pad = self.outline_width
        self.setGeometry(x - pad, y - pad, w + (pad * 2), h + (pad * 2))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Draw outline border
        pen = QPen(QColor(self.outline_color_hex), self.outline_width, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        half = cast(int, self.outline_width / 2.0)
        painter.drawRect(
            half,
            half,
            self.width() - self.outline_width,
            self.height() - self.outline_width
        )

        # 2. Draw translation overlays if scan_results are present
        if self.scan_results:
            overlay_color_hex = self.config_manager.get("translate_overlay_color")
            bg_color = QColor.fromString(overlay_color_hex)

            font_color_hex = self.config_manager.get("translate_font_color")
            fg_color = QColor.fromString(font_color_hex)

            # Setup Font
            font = painter.font()
            font_path = self.config_manager.get("translate_font_path")
            if font_path and os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        font = QFont(families[0])

            # Draw each result
            pad = self.outline_width

            painter.save()
            painter.translate(pad, pad)

            for res in self.scan_results:
                # Loop through all coordinates of the polygon to build it dynamically
                poly_points = [QPointF(pt[0], pt[1]) for pt in res.box]
                if len(poly_points) < 3:
                    continue

                # 1. Draw an overlay background as a filled polygon
                poly = QPolygonF(poly_points)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(bg_color)
                painter.drawPolygon(poly)

                # 2. Calculate text direction, width and height of the box
                p0 = poly_points[0]
                p1 = poly_points[1]
                p_last = poly_points[-1]

                dx = p1.x() - p0.x()
                dy = p1.y() - p0.y()
                width = math.sqrt(dx ** 2 + dy ** 2)

                h_dx = p_last.x() - p0.x()
                h_dy = p_last.y() - p0.y()
                height = math.sqrt(h_dx ** 2 + h_dy ** 2)

                angle_rad = math.atan2(dy, dx)
                angle_deg = math.degrees(angle_rad)

                # Save painter state to apply transformation locally
                painter.save()

                # Translate to top-left of the box (p0) and rotate
                painter.translate(p0.x(), p0.y())
                painter.rotate(angle_deg)

                # Define the local coordinate rectangle
                local_rect = QRectF(0, 0, width, height)

                # Scale font size dynamically
                from PySide6.QtGui import QFontMetrics
                font_size = max(4, int(height - 2))
                font.setPixelSize(font_size)

                while font_size > 5:
                    font.setPixelSize(font_size)
                    metrics = QFontMetrics(font)
                    text_width = metrics.horizontalAdvance(res.translated_text)
                    text_height = metrics.height()
                    if text_width <= width and text_height <= height:
                        break
                    font_size -= 1

                painter.setFont(font)

                # Draw drop shadow for contrast
                painter.setPen(QColor(0, 0, 0, 200))
                painter.drawText(local_rect.translated(1, 1), Qt.AlignmentFlag.AlignCenter, res.translated_text)

                # Draw foreground text
                painter.setPen(fg_color)
                painter.drawText(local_rect, Qt.AlignmentFlag.AlignCenter, res.translated_text)

                # Restore coordinate system
                painter.restore()

            painter.restore()
