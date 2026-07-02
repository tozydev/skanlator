import logging

from PySide6.QtCore import Qt, Slot, QSize, QPointF
from PySide6.QtGui import QColor, QPainter, QBrush, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QToolBar, QWidget, QSizePolicy, QDialog,
    QVBoxLayout, QGraphicsDropShadowEffect, QLabel
)

from app.worker import SkanlatorController
from core import CaptureRegion, ServiceStatus
from .icons import (
    create_custom_icon, draw_play, draw_stop, draw_crop, draw_settings, draw_close,
    draw_status_loading, draw_status_not_ready, draw_status_ready
)
from .overlay import OverlayRegion
from .region_select import RegionSelector
from .settings import SettingsDialog
from .utils import prevent_screen_capture, set_app_icon

logger = logging.getLogger(__name__)


class DragHandle(QWidget):
    """A designated widget placed on the toolbar to act as the drag handle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(16)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setToolTip("Giữ và kéo để di chuyển toolbar")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        # Dynamic theme-friendly gray dots
        painter.setBrush(QBrush(QColor(128, 128, 128, 180)))

        cx = self.width() / 2
        cy = self.height() / 2
        # Draw two columns of three gripper dots
        dots_y = [cy - 8, cy - 2, cy + 4]
        for dy in dots_y:
            painter.drawEllipse(QPointF(cx - 2.5, dy), 1.5, 1.5)
            painter.drawEllipse(QPointF(cx + 2.5, dy), 1.5, 1.5)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Set drag position on parent window
            self.window().drag_position = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        window = self.window()
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(window, 'drag_position'):
            window.move(event.globalPosition().toPoint() - window.drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.window().drag_position = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class FloatingToolbar(QWidget):
    def __init__(self, controller: SkanlatorController):
        super().__init__()
        self.controller = controller
        self.config_manager = controller.config_manager
        self.is_running = False
        self.service_ready = False
        self.drag_position = None
        self.outline_window = None

        # Connect to controller's forwarding signals
        self.controller.scan_success.connect(self.on_scan_success)
        self.controller.screen_updated.connect(self.on_screen_updated)
        self.controller.status_changed.connect(self.on_status_changed)

        self._init_ui()
        self._load_initial_region()
        self._update_action_toggle_disabled()

    def _init_ui(self):
        # Window configuration: Frameless, Always on Top, Tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        set_app_icon(self, "skanlator.ico")

        # Layout with padding/margins to allow space for the drop shadow
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        # Create QToolBar inside layout
        self.toolbar = QToolBar(self)
        self.toolbar.setIconSize(QSize(20, 20))
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)

        # Add tiny padding to the toolbar for a clean look
        self.toolbar.setStyleSheet("""
            QToolBar {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px;
            }
        """)

        # Apply Drop Shadow Effect to the QToolBar
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 90))  # ~35% opacity drop shadow
        self.toolbar.setGraphicsEffect(shadow)

        # 1. Add Drag Handle at the beginning of the toolbar
        self.handle = DragHandle(self)
        self.toolbar.addWidget(self.handle)

        # Service status icons
        self.status_ready_icon = create_custom_icon(draw_status_ready, size=24)
        self.status_not_ready_icon = create_custom_icon(draw_status_not_ready, size=24)
        self.status_loading_icon = create_custom_icon(draw_status_loading, size=24)

        # Service Status Indicator
        self.service_status_indicator = QLabel(self)
        self.service_status_indicator.setPixmap(self.status_loading_icon.pixmap(16, 16))
        self.service_status_indicator.setToolTip("Service status: Initializing...")
        self.toolbar.addWidget(self.service_status_indicator)

        # Define clean icons
        self.play_icon = create_custom_icon(draw_play, size=24)
        self.stop_icon = create_custom_icon(draw_stop, size=24)
        self.crop_icon = create_custom_icon(draw_crop, size=24)
        self.settings_icon = create_custom_icon(draw_settings, size=24)
        self.close_icon = create_custom_icon(draw_close, size=24)

        # Add actions to self.toolbar
        self.action_toggle = self.toolbar.addAction(self.play_icon, "Start")
        self.action_toggle.setToolTip("Bắt đầu dịch / Quét (Start)")
        self.action_toggle.triggered.connect(self.on_toggle_clicked)

        self.action_select = self.toolbar.addAction(self.crop_icon, "Select Area")
        self.action_select.setToolTip("Chọn vùng màn hình (Select Area)")
        self.action_select.triggered.connect(self.on_select_clicked)

        self.action_settings = self.toolbar.addAction(self.settings_icon, "Settings")
        self.action_settings.setToolTip("Cấu hình & Cài đặt (Settings)")
        self.action_settings.triggered.connect(self.on_settings_clicked)

        self.toolbar.addSeparator()

        self.action_close = self.toolbar.addAction(self.close_icon, "Close")
        self.action_close.setToolTip("Đóng ứng dụng (Close)")
        self.action_close.triggered.connect(self.on_close_clicked)

        layout.addWidget(self.toolbar)

        # Adjust window size and center at the top of primary screen
        self.adjustSize()
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
            y = screen_geometry.y() + 40  # 40px margin from top
            self.move(x, y)

        # Exclude window from screen capture on Windows to prevent feedback loops
        prevent_screen_capture(self)

    def _load_initial_region(self):
        screens = QApplication.screens()
        monitor_val = self.config_manager.get("capture_monitor") or 1

        # Validate if monitor index exists in system screens list
        if not (1 <= monitor_val <= len(screens)):
            self.config_manager.set("capture_monitor", 1)
            # Clear region since old monitor is disconnected
            self.config_manager.set("capture_region", None)
            self.config_manager.save()

        region = self.config_manager.get("capture_region")
        color = self.config_manager.get("capture_outline_color")
        width = self.config_manager.get("capture_outline_width")
        if region:
            self.outline_window = OverlayRegion(region, self.config_manager, color, width)
            self.outline_window.show()

    def _update_action_toggle_disabled(self):
        has_region = self.config_manager.get("capture_region") is not None
        can_start = self.service_ready and has_region
        is_disabled = not self.is_running and not can_start
        logger.debug(
            f"Updating toggle: is_running={self.is_running}, service_ready={self.service_ready}, has_region={has_region}, can_start={can_start}, disabled={is_disabled}")
        self.action_toggle.setDisabled(is_disabled)

    def update_outline_style(self, hex_color, width):
        if self.outline_window is not None:
            self.outline_window.update_style(hex_color, width)

    def clear_outline_window(self):
        if self.outline_window is not None:
            self.outline_window.close()
            self.outline_window = None

    # --- Button Callbacks ---
    @Slot()
    def on_toggle_clicked(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.action_toggle.setIcon(self.stop_icon)
            self.action_toggle.setToolTip("Dừng quét")

            # Disable selection and settings actions to prevent issues while running
            self.action_select.setEnabled(False)
            self.action_settings.setEnabled(False)

            # Start scanning
            region_val = self.config_manager.get("capture_region")
            if region_val:
                global_x, global_y, w, h = region_val

                # Convert global coordinates to monitor-relative coordinates
                screens = QGuiApplication.screens()
                monitor_val = self.config_manager.get("capture_monitor") or 1
                if 1 <= monitor_val <= len(screens):
                    screen = screens[monitor_val - 1]
                    screen_geom = screen.geometry()
                    relative_left = global_x - screen_geom.x()
                    relative_top = global_y - screen_geom.y()
                else:
                    relative_left = global_x
                    relative_top = global_y

                region = CaptureRegion(
                    left=relative_left,
                    top=relative_top,
                    width=w,
                    height=h
                )
                self.controller.start_scanning(region)
        else:
            self.action_toggle.setIcon(self.play_icon)
            self.action_toggle.setToolTip("Bắt đầu quét")

            # Re-enable selection and settings actions when stopped
            self.action_select.setEnabled(True)
            self.action_settings.setEnabled(True)

            # Stop scanning
            self.controller.stop_scanning()

            # Clear overlays on stop
            if self.outline_window:
                self.outline_window.scan_results = []
                self.outline_window.update()

    @Slot()
    def on_select_clicked(self):
        # Stop scanning if running
        if self.is_running:
            self.on_toggle_clicked()

        # Reload configuration before selection to ensure the latest screen limit is enforced
        self.config_manager.load()

        # Hide toolbar and existing outline window to avoid capturing them
        self.hide()
        if self.outline_window is not None:
            self.outline_window.hide()

        # Ensure event loop handles hiding
        QApplication.processEvents()

        outline_color = self.config_manager.get("capture_outline_color")
        outline_width = self.config_manager.get("capture_outline_width")

        # Launch selection overlay passing the config_manager to restrict bounds to selected screen
        selector = RegionSelector(self.config_manager, outline_color)
        if selector.exec() == QDialog.DialogCode.Accepted and selector.selected_region:
            region = selector.selected_region
            self.config_manager.set("capture_region", region)
            self.config_manager.save()

            # Recreate outline window
            if self.outline_window is not None:
                self.outline_window.close()

            self.outline_window = OverlayRegion(region, self.config_manager, outline_color, outline_width)
            self.outline_window.show()
        else:
            # Restore outline window if canceled
            if self.outline_window is not None:
                self.outline_window.show()

        self.show()
        self._update_action_toggle_disabled()

    @Slot()
    def on_settings_clicked(self):
        # Stop scanning if running
        was_running = self.is_running
        if was_running:
            self.on_toggle_clicked()

        dialog = SettingsDialog(self.config_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Immediately update UI to reflect re-initialization
            self.service_ready = False
            self.service_status_indicator.setPixmap(self.status_loading_icon.pixmap(16, 16))
            self.service_status_indicator.setToolTip("Service status: Initializing...")
            self._update_action_toggle_disabled()

            # Recreate worker thread and re-initialize engine with updated settings
            self.controller.handle_settings_changed()

        self._update_action_toggle_disabled()

    @Slot()
    def on_close_clicked(self):
        if self.outline_window is not None:
            self.outline_window.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def closeEvent(self, event):
        if self.outline_window is not None:
            self.outline_window.close()
        event.accept()

    @Slot(object)
    def on_scan_success(self, event):
        if self.outline_window:
            self.outline_window.scan_results = event.results
            self.outline_window.update()

    # noinspection PyUnusedLocal
    @Slot(object)
    def on_screen_updated(self, event):
        if self.outline_window:
            self.outline_window.scan_results = []
            self.outline_window.update()

    @Slot(dict)
    def on_status_changed(self, status_data):
        status = status_data.get("status")
        logger.debug(f"Engine status changed: {status_data}")

        if status == "services_status":
            services = status_data.get("services", {})
            all_ready = all(s == ServiceStatus.READY for s in services.values())
            any_error = any(s == ServiceStatus.ERROR for s in services.values())

            if any_error:
                self.service_ready = False
                self.service_status_indicator.setPixmap(self.status_not_ready_icon.pixmap(16, 16))
                tooltip_text = "Service status: Error\n"
                for name, service_status in services.items():
                    tooltip_text += f"- {name.capitalize()}: {service_status.name}\n"
                self.service_status_indicator.setToolTip(tooltip_text)
            elif all_ready:
                self.service_ready = True
                self.service_status_indicator.setPixmap(self.status_ready_icon.pixmap(16, 16))
                self.service_status_indicator.setToolTip("Service status: Ready")
            else:
                self.service_ready = False
                self.service_status_indicator.setPixmap(self.status_loading_icon.pixmap(16, 16))
                tooltip_text = "Service status: Initializing...\n"
                for name, service_status in services.items():
                    tooltip_text += f"- {name.capitalize()}: {service_status.name}\n"
                self.service_status_indicator.setToolTip(tooltip_text)

        elif status == "error":
            self.service_ready = False
            self.service_status_indicator.setPixmap(self.status_not_ready_icon.pixmap(16, 16))
            self.service_status_indicator.setToolTip(
                f"Service status: Error\n{status_data.get('message', 'Unknown error')}")

        elif status in ("running", "stopped"):
            self.service_status_indicator.setToolTip(f"Service status: {status}")

        self._update_action_toggle_disabled()
