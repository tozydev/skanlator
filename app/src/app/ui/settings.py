import os

from PySide6.QtCore import Slot
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QDoubleSpinBox, QSpinBox, QPushButton, QFileDialog, QColorDialog, QComboBox, QPlainTextEdit
)

from app.config import ConfigManager


class SettingsDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        # Always reload configuration from disk before opening settings dialog
        self.config_manager.load()

        self.setWindowTitle("Cài đặt - Skanlator")
        self.resize(520, 520)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Tab Widget for grouping settings
        self.tab_widget = QTabWidget(self)

        # Build each tab using specialized helper methods
        self._init_capture_tab()
        self._init_ocr_tab()
        self._init_translation_tab()

        layout.addWidget(self.tab_widget)

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Lưu", self)
        self.btn_save.clicked.connect(self._save_settings)
        self.btn_cancel = QPushButton("Hủy bỏ", self)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _init_capture_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group_cap = QGroupBox("Quét màn hình", tab)
        form_cap = QFormLayout(group_cap)

        self.spin_interval = QDoubleSpinBox(self)
        self.spin_interval.setRange(0.05, 5.0)
        self.spin_interval.setSingleStep(0.05)
        self.spin_interval.setSuffix(" giây")
        form_cap.addRow("Chu kỳ quét (Interval):", self.spin_interval)

        self.spin_sensitivity = QDoubleSpinBox(self)
        self.spin_sensitivity.setRange(0.1, 5.0)
        self.spin_sensitivity.setSingleStep(0.1)
        form_cap.addRow("Độ nhạy (Sensitivity):", self.spin_sensitivity)

        # Monitor selection ComboBox with available system monitors (real names)
        self.combo_monitor = QComboBox(self)
        screens = QGuiApplication.screens()
        for i, screen in enumerate(screens):
            geom = screen.geometry()
            name = screen.name()
            # Clean up Windows-specific naming e.g., \\.\DISPLAY1 -> DISPLAY1
            display_name = name.split("\\\\.\\")[-1] if name.startswith("\\\\.\\") else name
            self.combo_monitor.addItem(
                f"{display_name} ({geom.width()}x{geom.height()})",
                i + 1
            )
        form_cap.addRow("Màn hình quét (Monitor):", self.combo_monitor)

        # Region Outline color input row with preview and picker
        outline_color_layout = QHBoxLayout()
        self.edit_outline_color = QLineEdit(self)
        self.edit_outline_color.textChanged.connect(self._update_outline_color_preview)

        self.outline_color_preview = QWidget(self)
        self.outline_color_preview.setFixedSize(24, 24)

        self.btn_pick_outline_color = QPushButton("Chọn màu...", self)
        self.btn_pick_outline_color.clicked.connect(self._pick_outline_color)

        outline_color_layout.addWidget(self.edit_outline_color)
        outline_color_layout.addWidget(self.outline_color_preview)
        outline_color_layout.addWidget(self.btn_pick_outline_color)
        form_cap.addRow("Màu viền vùng chọn:", outline_color_layout)

        # Outline border width option
        self.spin_outline_width = QSpinBox(self)
        self.spin_outline_width.setRange(1, 10)
        self.spin_outline_width.setSuffix(" px")
        form_cap.addRow("Độ dày viền:", self.spin_outline_width)

        layout.addWidget(group_cap)
        layout.addStretch()
        self.tab_widget.addTab(tab, "Chụp ảnh")

    def _init_ocr_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group_ocr = QGroupBox("Mô hình OCR (ONNX)", tab)
        form_ocr = QFormLayout(group_ocr)

        # OCR Det
        det_layout = QHBoxLayout()
        self.edit_ocr_det = QLineEdit(self)
        self.btn_browse_det = QPushButton("Chọn...", self)
        self.btn_browse_det.clicked.connect(lambda: self._browse_file(self.edit_ocr_det, "ONNX Files (*.onnx)"))
        det_layout.addWidget(self.edit_ocr_det)
        det_layout.addWidget(self.btn_browse_det)
        form_ocr.addRow("Mô hình phát hiện (Det):", det_layout)

        # OCR Rec
        rec_layout = QHBoxLayout()
        self.edit_ocr_rec = QLineEdit(self)
        self.btn_browse_rec = QPushButton("Chọn...", self)
        self.btn_browse_rec.clicked.connect(lambda: self._browse_file(self.edit_ocr_rec, "ONNX Files (*.onnx)"))
        rec_layout.addWidget(self.edit_ocr_rec)
        rec_layout.addWidget(self.btn_browse_rec)
        form_ocr.addRow("Mô hình nhận dạng (Rec):", rec_layout)

        layout.addWidget(group_ocr)
        layout.addStretch()
        self.tab_widget.addTab(tab, "OCR")

    def _init_translation_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group_trans = QGroupBox("Cấu hình dịch thuật & Giao diện", tab)
        form_trans = QFormLayout(group_trans)

        # Translucent Overlay background color settings
        color_layout = QHBoxLayout()
        self.edit_overlay_color = QLineEdit(self)
        self.edit_overlay_color.textChanged.connect(self._update_color_preview)

        self.color_preview = QWidget(self)
        self.color_preview.setFixedSize(24, 24)

        self.btn_pick_color = QPushButton("Chọn màu...", self)
        self.btn_pick_color.clicked.connect(self._pick_color)

        color_layout.addWidget(self.edit_overlay_color)
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.btn_pick_color)
        form_trans.addRow("Màu nền Overlay (RGBA):", color_layout)

        # Translucent Overlay font color settings
        font_color_layout = QHBoxLayout()
        self.edit_font_color = QLineEdit(self)
        self.edit_font_color.textChanged.connect(self._update_font_color_preview)

        self.font_color_preview = QWidget(self)
        self.font_color_preview.setFixedSize(24, 24)

        self.btn_pick_font_color = QPushButton("Chọn màu...", self)
        self.btn_pick_font_color.clicked.connect(self._pick_font_color)

        font_color_layout.addWidget(self.edit_font_color)
        font_color_layout.addWidget(self.font_color_preview)
        font_color_layout.addWidget(self.btn_pick_font_color)
        form_trans.addRow("Màu chữ Overlay (RGBA):", font_color_layout)

        # Font file path selector
        font_layout = QHBoxLayout()
        self.edit_font_path = QLineEdit(self)
        self.btn_browse_font = QPushButton("Chọn...", self)
        self.btn_browse_font.clicked.connect(self._browse_font)
        font_layout.addWidget(self.edit_font_path)
        font_layout.addWidget(self.btn_browse_font)
        form_trans.addRow("Đường dẫn Font:", font_layout)

        model_layout = QHBoxLayout()
        self.edit_trans_model = QLineEdit(self)
        self.btn_browse_trans = QPushButton("Chọn...", self)
        self.btn_browse_trans.clicked.connect(lambda: self._browse_file(self.edit_trans_model, "GGUF Files (*.gguf)"))
        model_layout.addWidget(self.edit_trans_model)
        model_layout.addWidget(self.btn_browse_trans)
        form_trans.addRow("Mô hình dịch (GGUF):", model_layout)

        self.edit_system_prompt = QPlainTextEdit(self)
        self.edit_system_prompt.setMinimumHeight(80)
        form_trans.addRow("System Prompt:", self.edit_system_prompt)

        self.spin_n_ctx = QSpinBox(self)
        self.spin_n_ctx.setRange(256, 32768)
        self.spin_n_ctx.setSingleStep(256)
        form_trans.addRow("Context Window:", self.spin_n_ctx)

        self.spin_temp = QDoubleSpinBox(self)
        self.spin_temp.setRange(0.0, 2.0)
        self.spin_temp.setSingleStep(0.1)
        form_trans.addRow("Temperature:", self.spin_temp)

        self.spin_top_p = QDoubleSpinBox(self)
        self.spin_top_p.setRange(0.0, 1.0)
        self.spin_top_p.setSingleStep(0.05)
        form_trans.addRow("Top P:", self.spin_top_p)

        self.spin_max_tokens = QSpinBox(self)
        self.spin_max_tokens.setRange(1, 4096)
        form_trans.addRow("Max Tokens:", self.spin_max_tokens)

        layout.addWidget(group_trans)
        layout.addStretch()
        self.tab_widget.addTab(tab, "Dịch thuật")

    def _load_settings(self):
        cm = self.config_manager

        # Overlay Color & Font Path
        self.edit_overlay_color.setText(cm.get("translate_overlay_color"))
        self.edit_font_color.setText(cm.get("translate_font_color"))
        self.edit_font_path.setText(cm.get("translate_font_path"))

        # Capture
        self.spin_interval.setValue(cm.get("capture_interval"))
        self.spin_sensitivity.setValue(cm.get("capture_sensitivity"))

        # Load monitor combo selection
        monitor_val = cm.get("capture_monitor") or 1
        idx = self.combo_monitor.findData(monitor_val)
        if idx >= 0:
            self.combo_monitor.setCurrentIndex(idx)
        else:
            self.combo_monitor.setCurrentIndex(0)

        self.edit_outline_color.setText(cm.get("capture_outline_color"))
        self.spin_outline_width.setValue(cm.get("capture_outline_width"))

        # OCR
        self.edit_ocr_det.setText(cm.get("ocr_det_model_path"))
        self.edit_ocr_rec.setText(cm.get("ocr_rec_model_path"))

        # Translation
        self.edit_trans_model.setText(cm.get("translate_model_path"))
        self.edit_system_prompt.setPlainText(cm.get("translate_system_prompt"))
        self.spin_n_ctx.setValue(cm.get("translate_n_ctx"))
        self.spin_temp.setValue(cm.get("translate_temperature"))
        self.spin_top_p.setValue(cm.get("translate_top_p"))
        self.spin_max_tokens.setValue(cm.get("translate_max_tokens"))

    @Slot()
    def _save_settings(self):
        cm = self.config_manager

        # Check if monitor changed, and reset old region if so
        old_monitor = cm.get("capture_monitor")
        new_monitor = self.combo_monitor.currentData()
        if old_monitor != new_monitor:
            cm.set("capture_region", None)
            parent = self.parent()
            if hasattr(parent, "clear_outline_window"):
                parent.clear_outline_window()

        # Update Overlay Color & Font Path
        cm.set("translate_overlay_color", self.edit_overlay_color.text())
        cm.set("translate_font_color", self.edit_font_color.text())
        cm.set("translate_font_path", self.edit_font_path.text())

        # Capture
        cm.set("capture_interval", self.spin_interval.value())
        cm.set("capture_sensitivity", self.spin_sensitivity.value())
        cm.set("capture_monitor", new_monitor)
        cm.set("capture_outline_color", self.edit_outline_color.text())
        cm.set("capture_outline_width", self.spin_outline_width.value())

        # OCR
        cm.set("ocr_det_model_path", self.edit_ocr_det.text())
        cm.set("ocr_rec_model_path", self.edit_ocr_rec.text())

        # Translation
        cm.set("translate_model_path", self.edit_trans_model.text())
        cm.set("translate_system_prompt", self.edit_system_prompt.toPlainText())
        cm.set("translate_n_ctx", self.spin_n_ctx.value())
        cm.set("translate_temperature", self.spin_temp.value())
        cm.set("translate_top_p", self.spin_top_p.value())
        cm.set("translate_max_tokens", self.spin_max_tokens.value())

        cm.save()

        # Update parent outline window if open
        parent = self.parent()
        if hasattr(parent, "update_outline_style"):
            parent.update_outline_style(
                self.edit_outline_color.text(),
                self.spin_outline_width.value()
            )

        self.accept()

    # --- Color Support Helpers ---
    @Slot(str)
    def _update_font_color_preview(self, text):
        color = QColor(text)
        if color.isValid():
            self.font_color_preview.setStyleSheet(
                f"background-color: {text}; border: 1px solid #7a7a7a; border-radius: 4px;")
        else:
            self.font_color_preview.setStyleSheet(
                "background-color: transparent; border: 1px dashed red; border-radius: 4px;")

    @Slot()
    def _pick_font_color(self):
        initial_color = QColor(self.edit_font_color.text())
        if not initial_color.isValid():
            initial_color = QColor("#FFFFFFFF")

        color = QColorDialog.getColor(initial_color, self, "Chọn màu chữ Overlay",
                                      QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.edit_font_color.setText(color.name(QColor.NameFormat.HexArgb))
    @Slot(str)
    def _update_color_preview(self, text):
        color = QColor(text)
        if color.isValid():
            self.color_preview.setStyleSheet(
                f"background-color: {text}; border: 1px solid #7a7a7a; border-radius: 4px;")
        else:
            self.color_preview.setStyleSheet(
                "background-color: transparent; border: 1px dashed red; border-radius: 4px;")

    @Slot()
    def _pick_color(self):
        initial_color = QColor(self.edit_overlay_color.text())
        if not initial_color.isValid():
            initial_color = QColor(0, 0, 0, 179)

        color = QColorDialog.getColor(initial_color, self, "Chọn màu Overlay",
                                      QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.edit_overlay_color.setText(color.name(QColor.NameFormat.HexArgb))

    @Slot(str)
    def _update_outline_color_preview(self, text):
        color = QColor(text)
        if color.isValid():
            self.outline_color_preview.setStyleSheet(
                f"background-color: {text}; border: 1px solid #7a7a7a; border-radius: 4px;")
        else:
            self.outline_color_preview.setStyleSheet(
                "background-color: transparent; border: 1px dashed red; border-radius: 4px;")

    @Slot()
    def _pick_outline_color(self):
        initial_color = QColor(self.edit_outline_color.text())
        if not initial_color.isValid():
            initial_color = QColor("#0078D4")

        color = QColorDialog.getColor(initial_color, self, "Chọn màu viền vùng chọn",
                                      QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.edit_outline_color.setText(color.name(QColor.NameFormat.HexArgb))

    # --- File/Folder Dialog Helper ---
    @staticmethod
    def _get_default_dir(file_path_str: str) -> str:
        if file_path_str:
            abs_path = os.path.abspath(file_path_str)
            dir_path = os.path.dirname(abs_path)
            if os.path.isdir(dir_path):
                return dir_path
        return os.getcwd()

    def _browse_font(self):
        default_dir = self._get_default_dir(self.edit_font_path.text())
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn Font chữ", default_dir, "Font Files (*.ttf *.otf *.woff)"
        )
        if file_path:
            self.edit_font_path.setText(file_path)

    def _browse_file(self, line_edit: QLineEdit, file_filter: str):
        default_dir = self._get_default_dir(line_edit.text())
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file mô hình", default_dir, file_filter
        )
        if file_path:
            line_edit.setText(file_path)
