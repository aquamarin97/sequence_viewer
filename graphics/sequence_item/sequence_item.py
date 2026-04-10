# graphics/sequence_item/sequence_item.py
from typing import Optional
import weakref
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QFont, QColor, QPen, QBrush
from PyQt5.QtWidgets import QGraphicsItem
import math
from graphics.sequence_item.sequence_glyph_cache import default_nucleotide_color_map, GLYPH_CACHE
from graphics.sequence_item.sequence_item_model import SequenceItemModel
from settings.theme import theme_manager
from settings.display_settings_manager import display_settings_manager

class SequenceGraphicsItem(QGraphicsItem):
    TEXT_MODE = SequenceItemModel.TEXT_MODE
    BOX_MODE = SequenceItemModel.BOX_MODE
    LINE_MODE = SequenceItemModel.LINE_MODE

    def __init__(self, sequence, char_width=12.0, char_height=18.0, row_index=0, color_map=None, parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption, True)
        self.row_index = row_index
        self._row_highlighted = False
        self._model = SequenceItemModel(sequence=sequence, char_width=char_width, char_height=char_height, color_map=color_map)
        self.font = QFont(display_settings_manager.sequence_font_family)
        self.font.setStyleHint(QFont.Monospace)
        self.font.setFixedPitch(True)
        self._applied_font_size = -1.0
        self._sync_font_from_model()
        _ref = weakref.ref(self)
        theme_manager.themeChanged.connect(lambda _, r=_ref: (s := r()) and s.update())
        try:
            from settings.color_styles import color_style_manager as _csm
            _csm.stylesChanged.connect(lambda r=_ref: (s := r()) and s._on_color_styles_changed())
        except: pass

    @property
    def sequence(self): return self._model.sequence
    @property
    def sequence_upper(self): return self._model.sequence_upper
    @property
    def length(self): return self._model.length
    @property
    def char_width(self): return self._model.char_width
    @property
    def char_height(self): return self._model.char_height
    @property
    def color_map(self): return self._model.color_map
    @property
    def display_mode(self): return self._model.display_mode
    @property
    def selection_range(self): return self._model.selection_range

    def set_char_width(self, new_width):
        if new_width <= 0: new_width = 0.001
        if abs(new_width - self.char_width) < 0.0001: return
        self.prepareGeometryChange()
        self._model.set_char_width(new_width)
        self._sync_font_from_model()
        self.update()

    def set_selection(self, start_col, end_col):
        self._model.set_selection(start_col, end_col); self.update()
    def set_multi_selection(self, ranges):
        self._model.set_multi_selection(ranges); self.update()
    def clear_selection(self):
        self._model.clear_selection(); self.update()
    def set_row_highlighted(self, highlighted):
        highlighted = bool(highlighted)
        if self._row_highlighted == highlighted:
            return
        self._row_highlighted = highlighted
        self.update()
    def set_lod_max_mode(self, mode):
        self._model.set_lod_max_mode(mode); self.update()

    def refresh_display_settings(self):
        """Font family, char_height ve size'ı display_settings_manager'dan yeniden uygula."""
        self.font.setFamily(display_settings_manager.sequence_font_family)
        new_ch = display_settings_manager.sequence_char_height
        if self._model.char_height != new_ch:
            self.prepareGeometryChange()
            self._model.set_char_height(new_ch)
        else:
            self._model._update_display_state()
        self._applied_font_size = -1.0
        self._sync_font_from_model()
        self.update()

    def _on_color_styles_changed(self):
        self._model.refresh_color_map(); self.update()
    def _sync_font_from_model(self):
        desired = float(self._model.current_font_size)
        if abs(desired - self._applied_font_size) < 0.001: return
        self.font.setPointSizeF(desired)
        self._applied_font_size = desired

    def boundingRect(self):
        return QRectF(0, 0, self.char_width * self.length, self.char_height)

    def paint(self, painter, option, widget=None):
        if option is None or option.exposedRect.isNull(): return
        painter.save()
        painter.setFont(self.font)
        t = theme_manager.current
        exposed = option.exposedRect
        effective_mode = self._model.get_effective_mode()
        cw, ch = self.char_width, self.char_height
        length = self.length
        seq, seq_upper, color_map = self.sequence, self.sequence_upper, self.color_map
        if self._row_highlighted:
            row_bg = QColor(t.row_band_highlight)
        else:
            row_bg = t.row_bg_even if self.row_index % 2 == 0 else t.row_bg_odd
        painter.setPen(Qt.NoPen); painter.setBrush(QBrush(row_bg)); painter.drawRect(exposed)
        total_width = length * cw
        visible_left = max(exposed.left(), 0.0)
        visible_right = min(exposed.right(), total_width)
        if visible_right <= visible_left: painter.restore(); return
        start_index = max(0, math.floor(visible_left / cw))
        end_index = min(length, math.ceil(visible_right / cw))
        sel_ranges = self._model._selection_ranges  # [(start_incl, end_excl), ...]
        if effective_mode == SequenceItemModel.LINE_MODE:
            vis_l, vis_r = max(exposed.left(), 0.0), min(exposed.right(), total_width)
            if vis_r > vis_l:
                line_h = self._model.line_height; y = (ch - line_h) / 2.0
                painter.setBrush(QBrush(t.seq_line_fg)); painter.setPen(Qt.NoPen)
                painter.drawRect(QRectF(vis_l, y, vis_r - vis_l, line_h))
            if sel_ranges:
                sel_color = QColor(t.seq_selection_bg)
                painter.setBrush(QBrush(sel_color)); painter.setPen(Qt.NoPen)
                for s, e in sel_ranges:
                    sx = max(s * cw, vis_l); ex = min(e * cw, vis_r)
                    if ex > sx:
                        painter.drawRect(QRectF(sx, 0, ex - sx, ch))
            painter.restore(); return
        if sel_ranges:
            sel_color = QColor(t.seq_selection_bg)
            painter.setBrush(QBrush(sel_color)); painter.setPen(Qt.NoPen)
            for s, e in sel_ranges:
                sel_l = max(s, start_index); sel_r = min(e, end_index)
                if sel_r > sel_l:
                    for i in range(sel_l, sel_r): painter.drawRect(QRectF(i * cw, 0, cw, ch))
        if effective_mode == SequenceItemModel.TEXT_MODE:
            painter.setPen(Qt.NoPen); painter.setBrush(Qt.NoBrush)
            for i in range(start_index, end_index):
                base, base_u, x = seq[i], seq_upper[i], i * cw
                is_selected = any(s <= i < e for s, e in sel_ranges)
                color = QColor(255, 255, 255) if is_selected else color_map.get(base_u, QColor(50,50,50))
                glyph = GLYPH_CACHE.get_glyph(base, self.font, color)
                dx = x + (cw - glyph.width()) / 2.0; dy = (ch - glyph.height()) / 2.0
                painter.drawPixmap(QPointF(dx, dy), glyph)
        elif effective_mode == SequenceItemModel.BOX_MODE:
            painter.setPen(Qt.NoPen); box_h = self._model.box_height; y = (ch - box_h) / 2.0
            for i in range(start_index, end_index):
                base_u, x = seq_upper[i], i * cw
                color = color_map.get(base_u, QColor(50,50,50))
                painter.setBrush(QBrush(color)); painter.drawRect(QRectF(x, y, cw, box_h))
        painter.restore()
