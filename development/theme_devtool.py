from __future__ import annotations

from dataclasses import fields

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

from settings.theme import AppTheme, THEME_COLOR_FIELDS, clone_theme, theme_manager


def _color_to_text(color: QColor) -> str:
    if color.alpha() == 255:
        return f"rgb({color.red()}, {color.green()}, {color.blue()})"
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"


def _to_qcolor(value) -> QColor:
    return QColor(value) if isinstance(value, QColor) else QColor(str(value))


def _value_to_source(value) -> str:
    color = _to_qcolor(value)
    if isinstance(value, str):
        return f"\"{color.name().upper()}\""
    if color.alpha() == 255:
        return f"QColor({color.red()}, {color.green()}, {color.blue()})"
    return f"QColor({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"


def export_theme_code(light_theme: AppTheme, dark_theme: AppTheme) -> str:
    def render(theme: AppTheme, variable_name: str) -> str:
        lines = [f"{variable_name} = AppTheme(", f"    name=\"{theme.name}\","]
        for field_name in THEME_COLOR_FIELDS:
            lines.append(f"    {field_name}={_value_to_source(getattr(theme, field_name))},")
        lines.append(")")
        return "\n".join(lines)

    return "\n".join(
        [
            "from PyQt5.QtGui import QColor",
            "from settings.theme import AppTheme",
            "",
            render(light_theme, "LIGHT_THEME"),
            "",
            render(dark_theme, "DARK_THEME"),
        ]
    )


class ColorRowWidget(QWidget):
    def __init__(self, field_name: str, value, get_current_value, on_pick, parent=None):
        super().__init__(parent)
        self._field_name = field_name
        self._get_current_value = get_current_value
        self._on_pick = on_pick

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        self._name_label = QLabel(field_name, self)
        self._name_label.setMinimumWidth(190)
        self._value_label = QLabel(self)
        self._value_label.setMinimumWidth(170)

        self._preview_button = QPushButton(self)
        self._preview_button.setFixedSize(44, 24)
        self._preview_button.clicked.connect(self._pick_color)

        layout.addWidget(self._name_label)
        layout.addWidget(self._value_label, 1)
        layout.addWidget(self._preview_button, 0, Qt.AlignRight)

        self.set_value(value)

    def set_value(self, value):
        color = _to_qcolor(value)
        self._value_label.setText(_color_to_text(color))
        self._preview_button.setStyleSheet(
            "QPushButton {"
            f"background:{color.name(QColor.HexArgb) if color.alpha() < 255 else color.name()};"
            "border:1px solid #666;"
            "border-radius:4px;"
            "}"
        )

    def _pick_color(self):
        current = _to_qcolor(self._get_current_value(self._field_name))
        picked = QColorDialog.getColor(current, self, self._field_name, QColorDialog.ShowAlphaChannel)
        if picked.isValid():
            self._on_pick(self._field_name, picked)


class ThemePaletteTab(QWidget):
    def __init__(self, theme_name: str, dialog, parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self._dialog = dialog
        self._rows = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        container = QWidget(scroll)
        scroll.setWidget(container)

        content = QVBoxLayout(container)
        content.setContentsMargins(8, 8, 8, 8)
        content.setSpacing(0)

        for field_name in THEME_COLOR_FIELDS:
            row = ColorRowWidget(
                field_name,
                self.get_value(field_name),
                self.get_value,
                self._on_pick,
                container,
            )
            self._rows[field_name] = row
            content.addWidget(row)

            line = QFrame(container)
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            content.addWidget(line)

        content.addStretch(1)

    def get_value(self, field_name: str):
        return getattr(self._dialog.working_theme(self._theme_name), field_name)

    def refresh(self):
        theme = self._dialog.working_theme(self._theme_name)
        for field_name, row in self._rows.items():
            row.set_value(getattr(theme, field_name))

    def _on_pick(self, field_name: str, color: QColor):
        self._dialog.update_theme_color(self._theme_name, field_name, color)


class ThemeDevelopmentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Development - Theme Palette")
        self.resize(600, 700)

        self._applied = {
            "light": clone_theme(theme_manager.theme("light")),
            "dark": clone_theme(theme_manager.theme("dark")),
        }
        self._working = {
            "light": clone_theme(self._applied["light"]),
            "dark": clone_theme(self._applied["dark"]),
        }
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self._tabs = QTabWidget(self)
        self._tabs.addTab(ThemePaletteTab("light", self, self._tabs), "Light Theme")
        self._tabs.addTab(ThemePaletteTab("dark", self, self._tabs), "Dark Theme")
        self._tabs.setCurrentIndex(0 if theme_manager.current.name == "light" else 1)
        layout.addWidget(self._tabs)

        buttons = QDialogButtonBox(self)
        self._reset_button = buttons.addButton("Reset", QDialogButtonBox.ResetRole)
        self._apply_button = buttons.addButton("Apply", QDialogButtonBox.ApplyRole)
        self._export_button = buttons.addButton("Export", QDialogButtonBox.ActionRole)
        self._close_button = buttons.addButton("Close", QDialogButtonBox.RejectRole)
        layout.addWidget(buttons)

        self._reset_button.clicked.connect(self._reset_current_theme)
        self._apply_button.clicked.connect(self._apply_changes)
        self._export_button.clicked.connect(self._export_changes)
        self._close_button.clicked.connect(self.reject)

    def working_theme(self, theme_name: str) -> AppTheme:
        return self._working[theme_name]

    def current_theme_name(self) -> str:
        return "dark" if self._tabs.currentIndex() == 1 else "light"

    def update_theme_color(self, theme_name: str, field_name: str, color: QColor):
        current = self._working[theme_name]
        values = {field.name: getattr(current, field.name) for field in fields(AppTheme)}
        existing = values[field_name]
        values[field_name] = color.name().upper() if isinstance(existing, str) else QColor(color)
        self._working[theme_name] = AppTheme(**values)
        self._refresh_tabs()
        theme_manager.set_theme(self._working[theme_name])

    def _refresh_tabs(self):
        for index in range(self._tabs.count()):
            self._tabs.widget(index).refresh()

    def _reset_current_theme(self):
        theme_name = self.current_theme_name()
        self._working[theme_name] = theme_manager.default_theme(theme_name)
        self._refresh_tabs()
        theme_manager.set_theme(self._working[theme_name])

    def _apply_changes(self):
        self._applied = {
            "light": clone_theme(self._working["light"]),
            "dark": clone_theme(self._working["dark"]),
        }
        theme_manager.set_theme(self._applied["light"])
        theme_manager.set_theme(self._applied["dark"])

    def _export_changes(self):
        code = export_theme_code(self._working["light"], self._working["dark"])
        QApplication.clipboard().setText(code)
        QMessageBox.information(self, "Export", "Tema kodu panoya kopyalandi.")

    def reject(self):
        theme_manager.set_theme(self._applied["light"])
        theme_manager.set_theme(self._applied["dark"])
        super().reject()
