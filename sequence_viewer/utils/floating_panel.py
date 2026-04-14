# sequence_viewer/utils/floating_panel.py
# utils/floating_panel.py
"""
FloatingPanel — theme-aware embedded overlay panel.

Viewport'a çocuk widget olarak eklenir; top-level pencere DEĞİLdir.
Bu sayede uygulama arka plana alındığında otomatik kaybolur.

Usage
-----
    panel = FloatingPanel(parent=viewport_widget)

    # Show with content (viewport-local coords):
    panel.update_content([("", "156 bp  62.3 °C")])
    panel.show_at(QPoint(x, y))   # bottom-right anchor in viewport coords

    # Hide:
    panel.clear_panel()
"""
from __future__ import annotations

from typing import Sequence

from PyQt5.QtCore import Qt, QPoint, QRect, QRectF, QSize
from PyQt5.QtGui import (
    QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen,
)
from PyQt5.QtWidgets import QWidget

from sequence_viewer.settings.theme import theme_manager


# ── Layout constants ──────────────────────────────────────────────────────────
_PAD_H   = 10   # horizontal padding (left / right)
_PAD_V   = 7    # vertical padding (top / bottom)
_ROW_GAP = 3    # extra gap between rows
_COL_GAP = 12   # gap between label column and value column
_RADIUS  = 5    # corner radius

# Seçimin sağ-alt köşesinden panel mesafesi (viewport px)
_ANCHOR_OFFSET_X = 0
_ANCHOR_OFFSET_Y = 4


# ── Color palette ─────────────────────────────────────────────────────────────

_DARK = dict(
    bg     = QColor(80,  84,  98, 238),
    border = QColor(115, 120, 138, 220),
    label  = QColor(185, 190, 208),
    value  = QColor(235, 238, 248),
)

_LIGHT = dict(
    bg     = QColor(218, 221, 230, 238),
    border = QColor(160, 165, 180, 220),
    label  = QColor( 55,  60,  78),
    value  = QColor( 15,  17,  25),
)


def _panel_colors(theme) -> tuple[QColor, QColor, QColor, QColor]:
    p = _DARK if theme.name == "dark" else _LIGHT
    return p["bg"], p["border"], p["label"], p["value"]


# ── FloatingPanel ─────────────────────────────────────────────────────────────

class FloatingPanel(QWidget):
    """
    Compact overlay panel for (label, value) pairs.

    Viewport'ın çocuk widget'ıdır — top-level pencere değil.
    Mouse olaylarına şeffaftır; uygulama arka plana geçince kaybolur.

    show_at(anchor)  → anchor = viewport içindeki seçim sağ-alt köşesi
    clear_panel()    → gizle
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Çocuk widget — top-level flags YOK
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._label_font = QFont("Segoe UI", 9)
        self._label_font.setStyleHint(QFont.SansSerif)
        self._label_font.setWeight(QFont.DemiBold)

        self._value_font = QFont("Consolas", 9)
        self._value_font.setStyleHint(QFont.Monospace)
        self._value_font.setFixedPitch(True)
        self._value_font.setBold(True)

        self._rows: list[tuple[str, str]] = []
        self._layout_cache: _LayoutCache | None = None

        theme_manager.themeChanged.connect(self._on_theme_changed)
        self.hide()

    # ── Public API ────────────────────────────────────────────────────────────

    def update_content(self, rows: Sequence[tuple[str, str]]) -> None:
        """İçerik satırlarını güncelle ve widget boyutunu ayarla."""
        self._rows = list(rows)
        self._layout_cache = self._compute_layout()
        self.setFixedSize(self._layout_cache.size)
        self.update()

    def show_at(self, anchor: QPoint) -> None:
        """
        Paneli `anchor` noktasının (viewport koordinatı) sağ-altında göster.
        anchor = seçimin sağ-alt köşesi (viewport px).
        """
        if self._layout_cache is None:
            return

        x = anchor.x() + _ANCHOR_OFFSET_X
        y = anchor.y() + _ANCHOR_OFFSET_Y

        # Ebeveyn sınırları içinde kal
        parent = self.parentWidget()
        if parent is not None:
            pw, ph = parent.width(), parent.height()
            w,  h  = self.width(), self.height()
            if x + w > pw:
                x = anchor.x() - w       # sola kaydır
            if y + h > ph:
                y = anchor.y() - h - _ANCHOR_OFFSET_Y   # yukarı kaydır
            x = max(0, min(x, pw - w))
            y = max(0, min(y, ph - h))

        self.move(x, y)
        if not self.isVisible():
            self.show()
        self.raise_()
        self.update()

    def clear_panel(self) -> None:
        """Paneli gizle."""
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

        path = QPainterPath()
        path.addRoundedRect(
            QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
            _RADIUS, _RADIUS,
        )
        painter.fillPath(path, bg)
        painter.setPen(QPen(border, 1.0))
        painter.drawPath(path)

        for i, (label, value) in enumerate(self._rows):
            y_base = lc.row_baselines[i]

            if label:
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

        ascent  = max(lm_label.ascent(),   lm_value.ascent())
        descent = max(lm_label.descent(),  lm_value.descent())
        row_h   = ascent + descent + _ROW_GAP

        label_col_w = max(
            (lm_label.horizontalAdvance(lb) for lb, _ in self._rows), default=0
        )
        value_col_w = max(
            (lm_value.horizontalAdvance(vl) for _, vl in self._rows), default=0
        )

        if label_col_w > 0:
            total_w = _PAD_H + label_col_w + _COL_GAP + value_col_w + _PAD_H
            value_x = _PAD_H + label_col_w + _COL_GAP
        else:
            total_w = _PAD_H + value_col_w + _PAD_H
            value_x = _PAD_H

        total_h = _PAD_V + len(self._rows) * row_h + _PAD_V
        label_x = _PAD_H

        baselines = [
            _PAD_V + ascent + i * row_h
            for i in range(len(self._rows))
        ]

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
        self.size          = size
        self.label_x       = label_x
        self.value_x       = value_x
        self.label_col_w   = label_col_w
        self.value_col_w   = value_col_w
        self.row_h         = row_h
        self.ascent        = ascent
        self.row_baselines = row_baselines
