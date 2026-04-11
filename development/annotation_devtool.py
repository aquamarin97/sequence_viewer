from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from model.annotation import AnnotationType
from settings.color_styles import color_style_manager


ANNOTATION_ORDER = (
    AnnotationType.PRIMER,
    AnnotationType.PROBE,
    AnnotationType.REPEATED_REGION,
    AnnotationType.MISMATCH_MARKER,
)


def _color_to_text(color: QColor) -> str:
    return f"rgb({color.red()}, {color.green()}, {color.blue()})"


def _clone_annotation_map(palette):
    return {ann_type: QColor(color) for ann_type, color in palette.items()}


class AnnotationColorRow(QWidget):
    def __init__(self, ann_type, getter, setter, parent=None):
        super().__init__(parent)
        self._ann_type = ann_type
        self._getter = getter
        self._setter = setter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        self._name = QLabel(ann_type.name, self)
        self._name.setMinimumWidth(170)
        self._value = QLabel(self)
        self._value.setMinimumWidth(140)
        self._button = QPushButton(self)
        self._button.setFixedSize(44, 24)
        self._button.clicked.connect(self._pick)

        layout.addWidget(self._name)
        layout.addWidget(self._value, 1)
        layout.addWidget(self._button, 0, Qt.AlignRight)
        self.refresh()

    def refresh(self):
        color = QColor(self._getter())
        self._value.setText(_color_to_text(color))
        self._button.setStyleSheet(
            "QPushButton {"
            f"background:{color.name()};"
            "border:1px solid #666;"
            "border-radius:4px;"
            "}"
        )

    def _pick(self):
        picked = QColorDialog.getColor(QColor(self._getter()), self, self._ann_type.name)
        if picked.isValid():
            self._setter(picked)


class AnnotationDevToolDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Development - Annotation Colors")
        self.resize(450, 350)

        self._applied = _clone_annotation_map(color_style_manager.annotation_color_map())
        self._working = _clone_annotation_map(self._applied)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self._tabs = QTabWidget(self)
        layout.addWidget(self._tabs)

        tab = QWidget(self._tabs)
        self._tabs.addTab(tab, "Annotation Colors")

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        self._rows = []

        scroll = QScrollArea(tab)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tab_layout.addWidget(scroll)

        container = QWidget(scroll)
        scroll.setWidget(container)

        content = QVBoxLayout(container)
        content.setContentsMargins(8, 8, 8, 8)
        content.setSpacing(0)

        for ann_type in ANNOTATION_ORDER:
            row = AnnotationColorRow(
                ann_type,
                lambda a=ann_type: self._working[a],
                lambda color, a=ann_type: self._update_color(a, color),
                self,
            )
            self._rows.append(row)
            content.addWidget(row)

            line = QFrame(self)
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            content.addWidget(line)

        content.addStretch(1)

        buttons = QDialogButtonBox(self)
        self._reset_button = buttons.addButton("Reset", QDialogButtonBox.ResetRole)
        self._apply_button = buttons.addButton("Apply", QDialogButtonBox.ApplyRole)
        self._export_button = buttons.addButton("Export", QDialogButtonBox.ActionRole)
        self._close_button = buttons.addButton("Close", QDialogButtonBox.RejectRole)
        layout.addWidget(buttons)

        self._reset_button.clicked.connect(self._reset_colors)
        self._apply_button.clicked.connect(self._apply_changes)
        self._export_button.clicked.connect(self._export_changes)
        self._close_button.clicked.connect(self.reject)

    def _refresh_rows(self):
        for row in self._rows:
            row.refresh()

    def _update_color(self, ann_type, color):
        self._working[ann_type] = QColor(color)
        color_style_manager.set_annotation_color(ann_type, color)
        self._refresh_rows()

    def _reset_colors(self):
        color_style_manager.reset_annotation_colors()
        self._working = _clone_annotation_map(color_style_manager.annotation_color_map())
        self._refresh_rows()

    def _apply_changes(self):
        self._applied = _clone_annotation_map(color_style_manager.annotation_color_map())

    def _export_changes(self):
        lines = ["from PyQt5.QtGui import QColor", "_DEFAULT_ANNOTATION_COLORS = {"]
        for ann_type in ANNOTATION_ORDER:
            color = self._working[ann_type]
            lines.append(
                f"    AnnotationType.{ann_type.name}: QColor({color.red()}, {color.green()}, {color.blue()}),"
            )
        lines.append("}")
        QApplication.clipboard().setText(
            "\n".join(["from model.annotation import AnnotationType", *lines])
        )
        QMessageBox.information(self, "Export", "Annotation color kodu panoya kopyalandi.")

    def reject(self):
        for ann_type, color in self._applied.items():
            color_style_manager.set_annotation_color(ann_type, color)
        self._working = _clone_annotation_map(self._applied)
        super().reject()
