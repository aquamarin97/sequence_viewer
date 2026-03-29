# features/consensus_row/consensus_row_widget.py
from __future__ import annotations
import math
from typing import Optional

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics
from PyQt5.QtWidgets import QWidget, QScrollBar

from features.consensus_row.consensus_row_model import ConsensusRowModel
from graphics.sequence_item.sequence_glyph_cache import default_nucleotide_color_map, GLYPH_CACHE
from model.alignment_data_model import AlignmentDataModel
from model.consensus_calculator import ConsensusMethod
from settings.theme import theme_manager

_TEXT_THRESHOLD = 8.0
_BOX_THRESHOLD  = 5.0
_ROW_HEIGHT     = 20


class ConsensusRowWidget(QWidget):
    def __init__(self, alignment_model: AlignmentDataModel, sequence_viewer, parent=None):
        super().__init__(parent)
        self._alignment_model    = alignment_model
        self._sequence_viewer    = sequence_viewer
        self._initial_char_width = float(sequence_viewer.char_width)
        self._model = ConsensusRowModel(method=ConsensusMethod.PLURALITY)

        self._font = QFont("Courier New")
        self._font.setStyleHint(QFont.Monospace)
        self._font.setFixedPitch(True)

        # color_map — color_style_manager'dan alınır, stylesChanged'de yenilenir
        self._color_map = default_nucleotide_color_map()

        self.setFixedHeight(_ROW_HEIGHT)
        self.setMinimumWidth(0)

        self._alignment_model.rowAppended.connect(self._on_data_changed)
        self._alignment_model.rowRemoved.connect(self._on_data_changed)
        self._alignment_model.rowMoved.connect(self._on_data_changed)
        self._alignment_model.modelReset.connect(self._on_data_changed)

        hbar: QScrollBar = self._sequence_viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self.update)
        hbar.rangeChanged.connect(self.update)

        anim = getattr(self._sequence_viewer, "_zoom_animation", None)
        if anim is not None:
            anim.valueChanged.connect(self.update)

        theme_manager.themeChanged.connect(self._on_theme_changed)

        # Nükleotid paleti değişince color_map'i yenile
        try:
            from settings.color_styles import color_style_manager as _csm
            _csm.stylesChanged.connect(self._on_color_styles_changed)
        except Exception:
            pass

    def set_method(self, method, threshold=None):
        self._model.set_method(method, threshold)
        self.update()

    @property
    def current_method(self): return self._model.method
    @property
    def current_threshold(self): return self._model.threshold

    def _on_color_styles_changed(self) -> None:
        """Nükleotid paleti değişince color_map'i yenile."""
        self._color_map = default_nucleotide_color_map()
        self._model.invalidate()
        self.update()

    def _on_data_changed(self, *_args):
        self._model.invalidate()
        self.update()

    def _on_theme_changed(self, _theme):
        self.update()

    def _get_char_width(self):
        if hasattr(self._sequence_viewer, "_get_current_char_width"):
            return float(self._sequence_viewer._get_current_char_width())
        return float(self._sequence_viewer.char_width)

    def _get_view_left(self):
        return float(self._sequence_viewer.horizontalScrollBar().value())

    def _effective_mode(self, char_width):
        items = getattr(self._sequence_viewer, "sequence_items", None)
        if items:
            return items[0].display_mode
        cw_default = self._initial_char_width or 12.0
        scale = char_width / cw_default
        if scale >= 1.8:   font_size = 12.0
        elif scale >= 1.2: font_size = 10.0
        elif scale >= 0.7: font_size = 8.0
        else:              font_size = max(1.0, 18.0 * 0.6 * scale)
        if font_size >= _TEXT_THRESHOLD: return "text"
        if font_size >= _BOX_THRESHOLD:  return "box"
        return "line"

    def _sync_font_size(self, char_width):
        cw_default = self._initial_char_width or 12.0
        scale = char_width / cw_default
        if scale >= 1.8:   size = 12.0
        elif scale >= 1.2: size = 10.0
        elif scale >= 0.7: size = 8.0
        else:              size = max(1.0, 18.0 * 0.6 * scale)
        self._font.setPointSizeF(size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        rect   = self.rect()
        width  = rect.width()
        height = rect.height()
        t      = theme_manager.current

        painter.fillRect(rect, QBrush(t.row_bg_odd))
        painter.setPen(QPen(t.border_normal))
        painter.drawLine(0, height - 1, width, height - 1)

        sequences = [seq for _, seq in self._alignment_model.all_rows()]
        if not sequences:
            painter.setPen(QPen(t.text_primary))
            painter.setFont(self._font)
            painter.drawText(rect.adjusted(6, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, "—")
            painter.end()
            return

        consensus = self._model.get_consensus(sequences)
        if not consensus:
            painter.end()
            return

        cw        = self._get_char_width()
        view_left = self._get_view_left()
        if cw <= 0:
            painter.end()
            return

        self._sync_font_size(cw)
        painter.setFont(self._font)

        mode   = self._effective_mode(cw)
        ch     = float(height)
        length = len(consensus)

        start_col = max(0, int(math.floor(view_left / cw)))
        end_col   = min(length, int(math.ceil((view_left + width) / cw)))

        if mode == "line":
            line_h = ch * 0.3
            y      = (ch - line_h) / 2.0
            seq_end_x  = length * cw - view_left
            draw_width = max(0.0, min(float(width), seq_end_x))
            painter.setBrush(QBrush(t.seq_line_fg))   # tema rengi
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(0, y, draw_width, line_h))
            painter.end()
            return

        box_h = min(ch * 0.75, self._font.pointSizeF() * 1.4)
        box_y = (ch - box_h) / 2.0

        for col in range(start_col, end_col):
            base  = consensus[col].upper()
            x     = col * cw - view_left
            color = self._color_map.get(base, t.text_primary)

            if mode == "box":
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)
                painter.drawRect(QRectF(x, box_y, cw, box_h))
            else:  # text
                glyph = GLYPH_CACHE.get_glyph(base, self._font, color)
                dx    = x + (cw - glyph.width())  / 2.0
                dy    =     (ch - glyph.height()) / 2.0
                painter.drawPixmap(int(dx), int(dy), glyph)

        painter.end()