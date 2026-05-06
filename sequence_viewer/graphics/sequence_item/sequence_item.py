# sequence_viewer/graphics/sequence_item/sequence_item.py
# graphics/sequence_item/sequence_item.py
from typing import Optional
import weakref
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QFont, QColor, QPen, QBrush
from PyQt5.QtWidgets import QGraphicsItem
import math
from sequence_viewer.graphics.sequence_item.sequence_glyph_cache import default_nucleotide_color_map, GLYPH_CACHE
from sequence_viewer.graphics.sequence_item.sequence_item_model import SequenceItemModel
from sequence_viewer.settings.theme import theme_manager
from sequence_viewer.settings.display_settings_manager import display_settings_manager

class SequenceGraphicsItem(QGraphicsItem):
    TEXT_MODE = SequenceItemModel.TEXT_MODE
    BOX_MODE = SequenceItemModel.BOX_MODE
    LINE_MODE = SequenceItemModel.LINE_MODE

    def __init__(self, sequence, char_width=12.0, char_height=18.0, row_index=0, color_map=None, base_char_width=None, parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption, True)
        self.row_index = row_index
        self._row_highlighted = False
        self._model = SequenceItemModel(sequence=sequence, char_width=char_width, char_height=char_height, color_map=color_map, base_char_width=base_char_width)
        self.font = QFont(display_settings_manager.sequence_font_family)
        self.font.setStyleHint(QFont.Monospace)
        self.font.setFixedPitch(True)
        self._applied_font_size = -1.0
        self._sync_font_from_model()
        _ref = weakref.ref(self)
        theme_manager.themeChanged.connect(lambda _, r=_ref: (s := r()) and s.update())
        try:
            from sequence_viewer.settings.color_styles import color_style_manager as _csm
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
        if self._row_highlighted == highlighted: return
        self._row_highlighted = highlighted
        self.update()
    def set_lod_max_mode(self, mode):
        self._model.set_lod_max_mode(mode); self.update()

    def refresh_display_settings(self):
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

        exposed = option.exposedRect
        model = self._model
        cw = model.char_width
        char_h = model.char_height
        length = model.length
        t = theme_manager.current

        painter.save()

        # Row background — one drawRect, no per-char work
        painter.setPen(Qt.NoPen)
        if self._row_highlighted:
            painter.setBrush(QBrush(QColor(t.row_band_highlight)))
        else:
            painter.setBrush(QBrush(t.row_bg_even if self.row_index % 2 == 0 else t.row_bg_odd))
        painter.drawRect(exposed)

        total_width = length * cw
        vis_left = max(exposed.left(), 0.0)
        vis_right = min(exposed.right(), total_width)
        if vis_right <= vis_left:
            painter.restore()
            return

        start_idx = max(0, math.floor(vis_left / cw))
        end_idx   = min(length, math.ceil(vis_right / cw))
        vis_len   = end_idx - start_idx

        sel_ranges     = model._selection_ranges
        effective_mode = model.get_effective_mode()

        if effective_mode == SequenceItemModel.LINE_MODE:
            line_h = model.line_height
            y = (char_h - line_h) / 2.0
            painter.setBrush(QBrush(t.seq_line_fg))
            painter.drawRect(QRectF(vis_left, y, vis_right - vis_left, line_h))
            if sel_ranges:
                painter.setBrush(QBrush(QColor(t.seq_selection_bg)))
                for s, e in sel_ranges:
                    sx = max(s * cw, vis_left); ex = min(e * cw, vis_right)
                    if ex > sx:
                        painter.drawRect(QRectF(sx, 0.0, ex - sx, char_h))
            painter.restore()
            return

        # --- Selection: build O(vis_len) mask and draw one rect per range ---
        # Replaces O(vis_len * n_ranges) any() check and per-character drawRect.
        sel_mask = None
        if sel_ranges:
            sel_mask = bytearray(vis_len)  # 0 = normal, 1 = selected
            painter.setBrush(QBrush(QColor(t.seq_selection_bg)))
            for s, e in sel_ranges:
                lo = max(s, start_idx)
                hi = min(e, end_idx)
                if hi > lo:
                    sel_mask[lo - start_idx : hi - start_idx] = b'\x01' * (hi - lo)
                    painter.drawRect(QRectF(lo * cw, 0.0, (hi - lo) * cw, char_h))

        seq       = model.sequence
        seq_upper = model.sequence_upper
        color_map = model.color_map
        _fallback = QColor(50, 50, 50)

        if effective_mode == SequenceItemModel.TEXT_MODE:
            painter.setFont(self.font)
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.NoBrush)
            _white = QColor(255, 255, 255)

            # Local glyph dicts use a single-char key instead of the 8-tuple
            # GLYPH_CACHE key — O(1) hits after the first encounter per base.
            # For ATGCN: ≤5 GLYPH_CACHE calls total per paint, rest are local hits.
            _local_normal: dict = {}
            _local_sel: dict = {}
            dy = 0.0

            for j in range(vis_len):
                i = start_idx + j
                base_char = seq[i]
                base_u    = seq_upper[i]

                if sel_mask is not None and sel_mask[j]:
                    pm = _local_sel.get(base_char)
                    if pm is None:
                        pm = GLYPH_CACHE.get_glyph(base_char, self.font, _white)
                        _local_sel[base_char] = pm
                else:
                    pm = _local_normal.get(base_char)
                    if pm is None:
                        col = color_map.get(base_u, _fallback)
                        pm  = GLYPH_CACHE.get_glyph(base_char, self.font, col)
                        _local_normal[base_char] = pm

                # dy is identical for every glyph at a given font size; compute once
                if not dy:
                    dy = (char_h - pm.height()) / 2.0

                x = i * cw
                painter.drawPixmap(QPointF(x + (cw - pm.width()) / 2.0, dy), pm)

        elif effective_mode == SequenceItemModel.BOX_MODE:
            box_h = model.box_height
            y = (char_h - box_h) / 2.0
            painter.setPen(Qt.NoPen)

            # Group x-positions by color → ≤5 setBrush calls for ATGCN instead of one per char
            buckets: dict = {}  # (r,g,b) -> [QColor, [x, ...]]
            for j in range(vis_len):
                i      = start_idx + j
                base_u = seq_upper[i]
                color  = color_map.get(base_u, _fallback)
                rgb    = (color.red(), color.green(), color.blue())
                entry  = buckets.get(rgb)
                if entry is None:
                    buckets[rgb] = [color, [i * cw]]
                else:
                    entry[1].append(i * cw)

            for _rgb, (color, xs) in buckets.items():
                painter.setBrush(QBrush(color))
                for x in xs:
                    painter.drawRect(QRectF(x, y, cw, box_h))

        painter.restore()
