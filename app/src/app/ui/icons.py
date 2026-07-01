import math

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPolygonF


def create_custom_icon(draw_func, size=24):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_func(painter, size)
    painter.end()
    return QIcon(pixmap)


# noinspection PyUnusedLocal
def draw_play(painter: QPainter, size: int):
    """Modern Play Icon"""
    pen = QPen(QColor("#0078D4"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QBrush(QColor("#0078D4")))
    poly = QPolygonF([QPointF(9, 7), QPointF(17, 12), QPointF(9, 17)])
    painter.drawPolygon(poly)


# noinspection PyUnusedLocal
def draw_stop(painter: QPainter, size: int):
    """Modern Stop Icon"""
    pen = QPen(QColor("#E81123"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QBrush(QColor("#E81123")))
    painter.drawRoundedRect(8, 8, 8, 8, 1, 1)


# noinspection PyUnusedLocal
def draw_crop(painter: QPainter, size: int):
    """Selection Box Icon"""
    pen = QPen(QColor("#505050"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(5, 5, 14, 14)
    # Center crosshair
    pen_center = QPen(QColor("#0078D4"), 1.8, Qt.PenStyle.SolidLine)
    painter.setPen(pen_center)
    painter.drawLine(12, 9, 12, 15)
    painter.drawLine(9, 12, 15, 12)


def draw_settings(painter: QPainter, size: int):
    """Gear settings icon"""
    pen = QPen(QColor("#505050"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(8, 8, 8, 8)

    cx, cy = size / 2, size / 2
    for i in range(8):
        angle = i * (2 * math.pi / 8)
        x1 = cx + 5 * math.cos(angle)
        y1 = cy + 5 * math.sin(angle)
        x2 = cx + 7.5 * math.cos(angle)
        y2 = cy + 7.5 * math.sin(angle)
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))


# noinspection PyUnusedLocal
def draw_close(painter: QPainter, size: int):
    """Close cross 'X'"""
    pen = QPen(QColor("#E81123"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.drawLine(8, 8, 16, 16)
    painter.drawLine(16, 8, 8, 16)
