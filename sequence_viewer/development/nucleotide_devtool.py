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

from sequence_viewer.settings.color_styles import NUCLEOTIDE_BASE_ORDER, color_style_manager
from sequence_viewer.settings.theme import theme_manager


def _color_to_text(color: QColor) -> str:
    return f"rgb({color.red()}, {color.green()}, {color.blue()})" if color.alpha() == 255 else (
        f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"
    )


def _clone_palette(palette):
    return {base: QColor(color) for base, color in palette.items()}


def _palette_to_code(name: str, palette) -> str:
    lines = [f"{name} = {{"]
    for base in NUCLEOTIDE_BASE_ORDER:
        color = palette[base]
        lines.append(f"    \"{base}\": QColor({color.red()}, {color.green()}, {color.blue()}),")
    lines.append("}")
    return "\n".join(lines)


def _palette_literal(palette) -> str:
    lines = ["{"]
    for base in NUCLEOTIDE_BASE_ORDER:
        color = palette[base]
        lines.append(f"    \"{base}\": QColor({color.red()}, {color.green()}, {color.blue()}),")
    lines.append("}")
    return "\n".join(lines)


class BaseColorRow(QWidget):
    def __init__(self, label: str, getter, on_pick, parent=None):
        super().__init__(parent)
        self._label = label
        self._getter = getter
        self._on_pick = on_pick

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        self._name = QLabel(label, self)
        self._name.setMinimumWidth(160)
        self._value = QLabel(self)
        self._value.setMinimumWidth(150)
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
        picked = QColorDialog.getColor(QColor(self._getter()), self, self._label)
        if picked.isValid():
            self._on_pick(picked)


class PaletteTab(QWidget):
    def __init__(self, rows_factory, parent=None):
        super().__init__(parent)
        self._rows = []

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

        rows_factory(content, self._rows)
        content.addStretch(1)

    def refresh(self):
        for row in self._rows:
            row.refresh()


class NucleotideDevToolDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Development - Nucleotide Colors")
        self.resize(500, 500)

        self._applied = self._snapshot()
        self._working = self._snapshot()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self._tabs = QTabWidget(self)
        self._tabs.addTab(PaletteTab(self._build_light_rows, self._tabs), "Light Theme")
        self._tabs.addTab(PaletteTab(self._build_dark_rows, self._tabs), "Dark Theme")
        self._tabs.addTab(PaletteTab(self._build_consensus_rows, self._tabs), "Consensus")
        self._tabs.addTab(PaletteTab(self._build_deuteranopia_rows, self._tabs), "Colorblind: Deuteranopia")
        self._tabs.addTab(PaletteTab(self._build_protanopia_rows, self._tabs), "Colorblind: Protanopia")
        self._tabs.setCurrentIndex(self._default_tab_index())
        layout.addWidget(self._tabs)

        buttons = QDialogButtonBox(self)
        self._reset_button = buttons.addButton("Reset", QDialogButtonBox.ResetRole)
        self._apply_button = buttons.addButton("Apply", QDialogButtonBox.ApplyRole)
        self._export_button = buttons.addButton("Export", QDialogButtonBox.ActionRole)
        self._close_button = buttons.addButton("Close", QDialogButtonBox.RejectRole)
        layout.addWidget(buttons)

        self._reset_button.clicked.connect(self._reset_current_tab)
        self._apply_button.clicked.connect(self._apply_changes)
        self._export_button.clicked.connect(self._export_changes)
        self._close_button.clicked.connect(self.reject)

    def _snapshot(self):
        return {
            "theme_light": _clone_palette(color_style_manager.nucleotide_palette("light")),
            "theme_dark": _clone_palette(color_style_manager.nucleotide_palette("dark")),
            "consensus_light": _clone_palette(color_style_manager.consensus_palette("light")),
            "consensus_dark": _clone_palette(color_style_manager.consensus_palette("dark")),
            "deuteranopia": _clone_palette(color_style_manager.colorblind_palette("deuteranopia")),
            "protanopia": _clone_palette(color_style_manager.colorblind_palette("protanopia")),
        }

    def _default_tab_index(self) -> int:
        mode = color_style_manager.get_colorblind_mode()
        if mode == "deuteranopia":
            return 3
        if mode == "protanopia":
            return 4
        return 1 if theme_manager.current.name == "dark" else 0

    def _add_divider(self, layout):
        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

    def _add_section_title(self, layout, text):
        label = QLabel(text, self)
        label.setStyleSheet("font-weight:600; padding:8px 10px 4px 10px;")
        layout.addWidget(label)

    def _add_palette_rows(self, layout, rows, getter, setter):
        for base in NUCLEOTIDE_BASE_ORDER:
            row = BaseColorRow(base, lambda b=base: getter(b), lambda color, b=base: setter(b, color), self)
            rows.append(row)
            layout.addWidget(row)
            self._add_divider(layout)

    def _build_light_rows(self, layout, rows):
        self._add_palette_rows(
            layout,
            rows,
            lambda base: self._working["theme_light"][base],
            lambda base, color: self._update_theme_palette("light", base, color),
        )

    def _build_dark_rows(self, layout, rows):
        self._add_palette_rows(
            layout,
            rows,
            lambda base: self._working["theme_dark"][base],
            lambda base, color: self._update_theme_palette("dark", base, color),
        )

    def _build_consensus_rows(self, layout, rows):
        self._add_section_title(layout, "Light Consensus")
        self._add_palette_rows(
            layout,
            rows,
            lambda base: self._working["consensus_light"][base],
            lambda base, color: self._update_consensus_palette("light", base, color),
        )
        self._add_section_title(layout, "Dark Consensus")
        self._add_palette_rows(
            layout,
            rows,
            lambda base: self._working["consensus_dark"][base],
            lambda base, color: self._update_consensus_palette("dark", base, color),
        )

    def _build_deuteranopia_rows(self, layout, rows):
        self._add_palette_rows(
            layout,
            rows,
            lambda base: self._working["deuteranopia"][base],
            lambda base, color: self._update_colorblind_palette("deuteranopia", base, color),
        )

    def _build_protanopia_rows(self, layout, rows):
        self._add_palette_rows(
            layout,
            rows,
            lambda base: self._working["protanopia"][base],
            lambda base, color: self._update_colorblind_palette("protanopia", base, color),
        )

    def _refresh_tabs(self):
        for index in range(self._tabs.count()):
            self._tabs.widget(index).refresh()

    def _update_theme_palette(self, theme_name, base, color):
        key = "theme_dark" if theme_name == "dark" else "theme_light"
        self._working[key][base] = QColor(color)
        color_style_manager.set_theme_palette_color(theme_name, base, color)
        self._refresh_tabs()

    def _update_consensus_palette(self, theme_name, base, color):
        key = "consensus_dark" if theme_name == "dark" else "consensus_light"
        self._working[key][base] = QColor(color)
        color_style_manager.set_consensus_palette_color(theme_name, base, color)
        self._refresh_tabs()

    def _update_colorblind_palette(self, mode, base, color):
        self._working[mode][base] = QColor(color)
        color_style_manager.set_colorblind_palette_color(mode, base, color)
        self._refresh_tabs()

    def _reset_current_tab(self):
        index = self._tabs.currentIndex()
        if index == 0:
            color_style_manager.reset_theme_palette("light")
            self._working["theme_light"] = _clone_palette(color_style_manager.nucleotide_palette("light"))
        elif index == 1:
            color_style_manager.reset_theme_palette("dark")
            self._working["theme_dark"] = _clone_palette(color_style_manager.nucleotide_palette("dark"))
        elif index == 2:
            color_style_manager.reset_consensus_palette("light")
            color_style_manager.reset_consensus_palette("dark")
            self._working["consensus_light"] = _clone_palette(color_style_manager.consensus_palette("light"))
            self._working["consensus_dark"] = _clone_palette(color_style_manager.consensus_palette("dark"))
        elif index == 3:
            color_style_manager.reset_colorblind_palette("deuteranopia")
            self._working["deuteranopia"] = _clone_palette(color_style_manager.colorblind_palette("deuteranopia"))
        else:
            color_style_manager.reset_colorblind_palette("protanopia")
            self._working["protanopia"] = _clone_palette(color_style_manager.colorblind_palette("protanopia"))
        self._refresh_tabs()

    def _apply_changes(self):
        self._applied = self._snapshot()

    def _export_changes(self):
        code = "\n\n".join(
            [
                "from PyQt5.QtGui import QColor",
                _palette_to_code("_NUCLEOTIDE_COLORS_LIGHT", self._working["theme_light"]),
                _palette_to_code("_NUCLEOTIDE_COLORS_DARK", self._working["theme_dark"]),
                "_CONSENSUS_COLORS = {\n"
                "    \"light\": " + _palette_literal(self._working["consensus_light"]).replace("\n", "\n    ") + ",\n"
                "    \"dark\": " + _palette_literal(self._working["consensus_dark"]).replace("\n", "\n    ") + ",\n"
                "}",
                "_COLORBLIND_MODES = {\n"
                "    \"deuteranopia\": " + _palette_literal(self._working["deuteranopia"]).replace("\n", "\n    ") + ",\n"
                "    \"protanopia\": " + _palette_literal(self._working["protanopia"]).replace("\n", "\n    ") + ",\n"
                "}",
            ]
        )
        QApplication.clipboard().setText(code)
        QMessageBox.information(self, "Export", "Nucleotide color kodu panoya kopyalandi.")

    def reject(self):
        self._restore_snapshot(self._applied)
        super().reject()

    def _restore_snapshot(self, snapshot):
        for base, color in snapshot["theme_light"].items():
            color_style_manager.set_theme_palette_color("light", base, color)
        for base, color in snapshot["theme_dark"].items():
            color_style_manager.set_theme_palette_color("dark", base, color)
        for base, color in snapshot["consensus_light"].items():
            color_style_manager.set_consensus_palette_color("light", base, color)
        for base, color in snapshot["consensus_dark"].items():
            color_style_manager.set_consensus_palette_color("dark", base, color)
        for base, color in snapshot["deuteranopia"].items():
            color_style_manager.set_colorblind_palette_color("deuteranopia", base, color)
        for base, color in snapshot["protanopia"].items():
            color_style_manager.set_colorblind_palette_color("protanopia", base, color)
        self._working = self._snapshot()


