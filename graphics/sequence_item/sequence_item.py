# graphics/sequence_item/sequence_item.py

from typing import Optional

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QFont, QColor, QPen, QBrush
from PyQt5.QtWidgets import QGraphicsItem
import math

from graphics.sequence_item.sequence_glyph_cache import default_nucleotide_color_map, GLYPH_CACHE
from graphics.sequence_item.sequence_item_model import SequenceItemModel
from settings.theme import theme_manager


class SequenceGraphicsItem(QGraphicsItem):
    """
    Tek bir sekans satırı. Dark-mode uyumlu.

    Arkaplan, seçim ve line-mode renkleri theme_manager token'larından alınır.
    Class-level sabit brush'lar kaldırıldı — her paint() çağrısında
    geçerli temadan okunur (performans açısından önemsiz, doğruluk kritik).
    """

    TEXT_MODE = SequenceItemModel.TEXT_MODE
    BOX_MODE  = SequenceItemModel.BOX_MODE
    LINE_MODE = SequenceItemModel.LINE_MODE

    def __init__(
        self,
        sequence:   str,
        char_width: float = 12.0,
        char_height:float = 18.0,
        row_index:  int   = 0,
        color_map:  Optional[dict] = None,
        parent:     Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption, True)

        self.row_index = row_index   # zebra renk seçimi için

        self._model = SequenceItemModel(
            sequence=sequence,
            char_width=char_width,
            char_height=char_height,
            color_map=color_map or default_nucleotide_color_map(),
        )

        self.font = QFont("Courier New")
        self.font.setStyleHint(QFont.Monospace)
        self.font.setFixedPitch(True)

        self._applied_font_size: float = -1.0
        self._sync_font_from_model()

        # Tema değişince yeniden çiz
        theme_manager.themeChanged.connect(self.update)

    # ---- Model proxy ----

    @property
    def sequence(self)      -> str:   return self._model.sequence
    @property
    def sequence_upper(self)-> str:   return self._model.sequence_upper
    @property
    def length(self)        -> int:   return self._model.length
    @property
    def char_width(self)    -> float: return self._model.char_width
    @property
    def char_height(self)   -> int:   return self._model.char_height
    @property
    def color_map(self)     -> dict:  return self._model.color_map
    @property
    def display_mode(self)  -> str:   return self._model.display_mode
    @property
    def selection_range(self):        return self._model.selection_range

    # ---- Public API ----

    def set_char_width(self, new_width: float) -> None:
        if new_width <= 0:
            new_width = 0.001
        if abs(new_width - self.char_width) < 0.0001:
            return
        self.prepareGeometryChange()
        self._model.set_char_width(new_width)
        self._sync_font_from_model()
        self.update()

    def set_selection(self, start_col: int, end_col: int) -> None:
        self._model.set_selection(start_col, end_col)
        self.update()

    def clear_selection(self) -> None:
        self._model.clear_selection()
        self.update()

    def set_lod_max_mode(self, mode: Optional[str]) -> None:
        self._model.set_lod_max_mode(mode)
        self.update()

    # ---- Font sync ----

    def _sync_font_from_model(self) -> None:
        desired = float(self._model.current_font_size)
        if abs(desired - self._applied_font_size) < 0.001:
            return
        self.font.setPointSizeF(desired)
        self._applied_font_size = desired

    # ---- QGraphicsItem ----

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.char_width * self.length, self.char_height)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        if option is None or option.exposedRect.isNull():
            return

        painter.save()
        painter.setFont(self.font)

        t              = theme_manager.current   # ← tema tokenları
        exposed        = option.exposedRect
        effective_mode = self._model.get_effective_mode()

        cw         = self.char_width
        ch         = self.char_height
        length     = self.length
        seq        = self.sequence
        seq_upper  = self.sequence_upper
        color_map  = self.color_map

        # Arkaplan — zebra: çift/tek satır farklı ton
        row_bg = t.row_bg_even if self.row_index % 2 == 0 else t.row_bg_odd
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(row_bg))
        painter.drawRect(exposed)

        total_width   = length * cw
        visible_left  = max(exposed.left(), 0.0)
        visible_right = min(exposed.right(), total_width)
        if visible_right <= visible_left:
            painter.restore()
            return

        start_index = max(0, math.floor(visible_left  / cw))
        end_index   = min(length, math.ceil(visible_right / cw))

        sel_start = sel_end = None
        if self.selection_range is not None:
            sel_start, sel_end = self.selection_range

        # ---- LINE MODE ----
        if effective_mode == SequenceItemModel.LINE_MODE:
            vis_l = max(exposed.left(), 0.0)
            vis_r = min(exposed.right(), total_width)
            if vis_r > vis_l:
                line_h = self._model.line_height
                y      = (ch - line_h) / 2.0
                painter.setBrush(QBrush(t.seq_line_fg))
                painter.setPen(Qt.NoPen)
                painter.drawRect(QRectF(vis_l, y, vis_r - vis_l, line_h))
            painter.restore()
            return

        # ---- TEXT / BOX ----

        # Seçim arkaplanı
        if sel_start is not None and sel_end is not None:
            sel_l = max(sel_start, start_index)
            sel_r = min(sel_end,   end_index)
            if sel_r > sel_l:
                painter.setBrush(QBrush(t.seq_selection_bg))
                painter.setPen(Qt.NoPen)
                for i in range(sel_l, sel_r):
                    painter.drawRect(QRectF(i * cw, 0, cw, ch))

        if effective_mode == SequenceItemModel.TEXT_MODE:
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.NoBrush)
            for i in range(start_index, end_index):
                base   = seq[i]
                base_u = seq_upper[i]
                x      = i * cw
                color  = color_map.get(base_u, QColor(50, 50, 50))
                glyph  = GLYPH_CACHE.get_glyph(base, self.font, color)
                dx = x + (cw - glyph.width())  / 2.0
                dy =     (ch - glyph.height()) / 2.0
                painter.drawPixmap(QPointF(dx, dy), glyph)

        elif effective_mode == SequenceItemModel.BOX_MODE:
            painter.setPen(Qt.NoPen)
            box_h = self._model.box_height
            y     = (ch - box_h) / 2.0
            for i in range(start_index, end_index):
                base_u = seq_upper[i]
                x      = i * cw
                color  = color_map.get(base_u, QColor(50, 50, 50))
                painter.setBrush(QBrush(color))
                painter.drawRect(QRectF(x, y, cw, box_h))

        painter.restore()