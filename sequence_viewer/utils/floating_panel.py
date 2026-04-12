# utils/floating_panel.py
"""
FloatingPanel — reusable, theme-aware floating info panel.

Renders a compact two-column (label | value) list near the cursor.
Subscribes to theme_manager so light/dark changes are reflected
without any extra wiring by the caller.

Usage
-----
    panel = FloatingPanel()

    # Show with content:
    panel.update_content([("Bp", "156"), ("Tm", "62.3 °C")])
    panel.show_at(global_pos)

    # Hide:
    panel.clear_panel()

The panel is a top-level frameless window (Qt.ToolTip style) that
never steals focus and is transparent to mouse events.
"""
from __future__ import annotations

from typing import Sequence

from PyQt5.QtCore import Qt, QPoint, QRect, QRectF, QSize
from PyQt5.QtGui import (
    QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen,
)
from PyQt5.QtWidgets import QApplication, QWidget

from sequence_viewer.settings.theme import theme_manager


# ── Layout constants ──────────────────────────────────────────────────────────
_PAD_H = 10        # horizontal padding (left / right)
_PAD_V = 7         # vertical padding (top / bottom)
_ROW_GAP = 3       # extra gap between rows
_COL_GAP = 12      # gap between label column and value column
_RADIUS = 5        # corner radius of the background rect
_CURSOR_OFFSET_X = 14   # tooltip offset right of cursor
_CURSOR_OFFSET_Y = -50  # tooltip offset above cursor


# ── Color palette ─────────────────────────────────────────────────────────────
#
# Her iki tema için sabit renkler — token türetimi yerine bilinçli seçim.
# Bg renkleri alpha kanalı ile tanımlanır, border yarı-saydam.

_DARK = dict(
    bg     = QColor(80,  84,  98, 238),   # koyu gümüş-çelik
    border = QColor(115, 120, 138, 220),  # hafif parlak kenar
    label  = QColor(185, 190, 208),       # gümüş-beyaz, net okunur
    value  = QColor(235, 238, 248),       # parlak beyaz-mavi
)

_LIGHT = dict(
    bg     = QColor(218, 221, 230, 238),  # soğuk açık gri
    border = QColor(160, 165, 180, 220),  # orta gri kenar
    label  = QColor( 55,  60,  78),       # koyu lacivert-gri, net
    value  = QColor( 15,  17,  25),       # neredeyse siyah
)


def _panel_colors(theme) -> tuple[QColor, QColor, QColor, QColor]:
    """Returns (bg, border, label_fg, value_fg) for the given theme."""
    p = _DARK if theme.name == "dark" else _LIGHT
    return p["bg"], p["border"], p["label"], p["value"]


# ── FloatingPanel ─────────────────────────────────────────────────────────────

class FloatingPanel(QWidget):
    """
    Compact floating panel for showing (label, value) pairs.

    Subclass to create domain-specific floating displays; or use
    directly for generic ad-hoc info.

    Public API
    ----------
    update_content(rows)   → set / refresh the rows; resizes widget
    show_at(global_pos)    → position near cursor and show
    clear_panel()          → hide

    The widget connects itself to ``theme_manager.themeChanged`` and
    repaints automatically on theme switches.
    """

    def __init__(self) -> None:
        super().__init__(None)                          # top-level window
        self.setWindowFlags(
            Qt.ToolTip
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Font for labels — semi-bold so they read clearly alongside values
        self._label_font = QFont("Segoe UI", 9)
        self._label_font.setStyleHint(QFont.SansSerif)
        self._label_font.setWeight(QFont.DemiBold)

        # Font for values (monospace so numbers align cleanly)
        self._value_font = QFont("Consolas", 9)
        self._value_font.setStyleHint(QFont.Monospace)
        self._value_font.setFixedPitch(True)
        self._value_font.setBold(True)

        self._rows: list[tuple[str, str]] = []   # [(label, value), ...]
        self._layout_cache: _LayoutCache | None = None

        theme_manager.themeChanged.connect(self._on_theme_changed)
        self.hide()

    # ── Public API ────────────────────────────────────────────────────────────

    def update_content(self, rows: Sequence[tuple[str, str]]) -> None:
        """Set the displayed (label, value) pairs and resize the widget."""
        self._rows = list(rows)
        self._layout_cache = self._compute_layout()
        self.setFixedSize(self._layout_cache.size)
        self.update()

    def show_at(self, global_pos: QPoint) -> None:
        """Position the panel near *global_pos* (in global screen coords) and show."""
        if self._layout_cache is None:
            return
        x = global_pos.x() + _CURSOR_OFFSET_X
        y = global_pos.y() + _CURSOR_OFFSET_Y
        # Keep on screen
        screen = QApplication.screenAt(global_pos)
        if screen is not None:
            sg = screen.geometry()
            w, h = self.width(), self.height()
            if x + w > sg.right():
                x = global_pos.x() - w - 4
            if y < sg.top():
                y = global_pos.y() + 20
            x = max(sg.left(), x)
            y = max(sg.top(), min(y, sg.bottom() - h))
        self.move(x, y)
        if not self.isVisible():
            self.show()
        else:
            self.update()

    def clear_panel(self) -> None:
        """Hide the panel."""
        if self.isVisible():
            self.hide()

    # ── Qt overrides ──────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        if not self._rows or self._layout_cache is None:
            return

        t = theme_manager.current
        bg, border, label_fg, value_fg = _panel_colors(t)
        lc = self._layout_cache

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
                            _RADIUS, _RADIUS)
        painter.fillPath(path, bg)
        painter.setPen(QPen(border, 1.0))
        painter.drawPath(path)

        # Rows
        for i, (label, value) in enumerate(self._rows):
            y_base = lc.row_baselines[i]

            painter.setFont(self._label_font)
            painter.setPen(label_fg)
            painter.drawText(
                QRect(lc.label_x, y_base - lc.ascent, lc.label_col_w, lc.row_h),
                Qt.AlignRight | Qt.AlignVCenter,
                label,
            )

            painter.setFont(self._value_font)
            painter.setPen(value_fg)
            painter.drawText(
                QRect(lc.value_x, y_base - lc.ascent, lc.value_col_w, lc.row_h),
                Qt.AlignLeft | Qt.AlignVCenter,
                value,
            )

        painter.end()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _compute_layout(self) -> "_LayoutCache":
        lm_label = QFontMetrics(self._label_font)
        lm_value = QFontMetrics(self._value_font)

        ascent   = max(lm_label.ascent(), lm_value.ascent())
        descent  = max(lm_label.descent(), lm_value.descent())
        row_h    = ascent + descent + _ROW_GAP

        label_col_w = max((lm_label.horizontalAdvance(lb) for lb, _ in self._rows), default=0)
        value_col_w = max((lm_value.horizontalAdvance(vl) for _, vl in self._rows), default=0)

        total_w = _PAD_H + label_col_w + _COL_GAP + value_col_w + _PAD_H
        total_h = _PAD_V + len(self._rows) * row_h + _PAD_V

        label_x = _PAD_H
        value_x = _PAD_H + label_col_w + _COL_GAP

        baselines = []
        for i in range(len(self._rows)):
            baselines.append(_PAD_V + ascent + i * row_h)

        return _LayoutCache(
            size        = QSize(int(total_w), int(total_h)),
            label_x     = label_x,
            value_x     = value_x,
            label_col_w = label_col_w,
            value_col_w = value_col_w,
            row_h       = row_h,
            ascent      = ascent,
            row_baselines = baselines,
        )

    def _on_theme_changed(self, _theme) -> None:
        if self.isVisible():
            self.update()


# ── Internal layout data class ────────────────────────────────────────────────

class _LayoutCache:
    __slots__ = (
        "size", "label_x", "value_x",
        "label_col_w", "value_col_w",
        "row_h", "ascent", "row_baselines",
    )

    def __init__(self, *, size, label_x, value_x,
                 label_col_w, value_col_w, row_h, ascent, row_baselines):
        self.size         = size
        self.label_x      = label_x
        self.value_x      = value_x
        self.label_col_w  = label_col_w
        self.value_col_w  = value_col_w
        self.row_h        = row_h
        self.ascent       = ascent
        self.row_baselines = row_baselines
