# graphics/sequence_item.py

from typing import Optional

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter,
    QFont,
    QColor,
    QPen,
    QBrush,
)
from PyQt5.QtWidgets import QGraphicsItem
import math

from graphics.sequence_item.sequence_glyph_cache import default_nucleotide_color_map, GLYPH_CACHE
from graphics.sequence_item.sequence_item_model import SequenceItemModel


class SequenceGraphicsItem(QGraphicsItem):
    """
    Tek bir sekans satırı: sadece nt hücrelerini çizer (header yok).

    CMV:
    - Model : SequenceItemModel (sequence, zoom state, display_mode, selection)
    - View  : Bu sınıf (QGraphicsItem + paint/boundingRect)
    - Controller: Şimdilik yok; seçim ve zoom kararları SequenceViewer tarafında.
    """
    TEXT_MODE = SequenceItemModel.TEXT_MODE
    BOX_MODE = SequenceItemModel.BOX_MODE
    LINE_MODE = SequenceItemModel.LINE_MODE

    _BACKGROUND_BRUSH = QBrush(Qt.white)
    _LINE_BRUSH = QBrush(QColor(160, 160, 160))
    _SELECTION_BRUSH = QBrush(QColor(173, 216, 230))

    def __init__(
        self,
        sequence: str,
        char_width: float = 12.0,
        char_height: float = 18.0,
        color_map: Optional[dict] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)

        # Viewport-aware painting için:
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption, True)

        # Model
        self._model = SequenceItemModel(
            sequence=sequence,
            char_width=char_width,
            char_height=char_height,
            color_map=color_map or default_nucleotide_color_map(),
        )

        # Font (view tarafında)
        self.font = QFont("Courier New")
        self.font.setStyleHint(QFont.Monospace)
        self.font.setFixedPitch(True)

        self._applied_font_size: float = -1.0
        self._sync_font_from_model()

    # ----------------- Model proxy özellikler -----------------

    @property
    def sequence(self) -> str:
        return self._model.sequence

    @property
    def sequence_upper(self) -> str:
        return self._model.sequence_upper

    @property
    def length(self) -> int:
        return self._model.length

    @property
    def char_width(self) -> float:
        return self._model.char_width

    @property
    def char_height(self) -> int:
        return self._model.char_height

    @property
    def color_map(self) -> dict:
        return self._model.color_map

    @property
    def display_mode(self) -> str:
        return self._model.display_mode

    @property
    def selection_range(self) -> Optional[tuple]:
        return self._model.selection_range

    # ---------------- Public API ----------------

    def set_char_width(self, new_width: float) -> None:
        """
        Zoom sırasında SequenceViewerView tarafından çağrılır.
        """
        # Geometri değişeceği için önce prepareGeometryChange
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

    # ---------------- View içi yardımcılar ----------------

    def _sync_font_from_model(self) -> None:
        """
        Modeldeki current_font_size'ı QFont'a uygular.
        """
        desired_size = float(self._model.current_font_size)
        if abs(desired_size - self._applied_font_size) < 0.001:
            return

        self.font.setPointSizeF(desired_size)
        self._applied_font_size = desired_size

    # ---------------- QGraphicsItem interface ----------------

    def boundingRect(self) -> QRectF:
        width = self.char_width * self.length
        height = self.char_height
        return QRectF(0, 0, width, height)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        # Viewport-aware: sadece gerçekten boyanan bölge için çalış
        if option is None or option.exposedRect.isNull():
            return

        painter.save()
        painter.setFont(self.font)

        exposed = option.exposedRect

        effective_mode = self._model.get_effective_mode()

        cw = self.char_width
        ch = self.char_height
        length = self.length
        seq = self.sequence
        seq_upper = self.sequence_upper
        color_map = self.color_map

        # Arkaplan (sadece exposedRect kadar)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._BACKGROUND_BRUSH)
        painter.drawRect(exposed)

        total_width = length * cw
        visible_left = max(exposed.left(), 0.0)
        visible_right = min(exposed.right(), total_width)
        if visible_right <= visible_left:
            painter.restore()
            return

        start_index = max(0, math.floor(visible_left / cw))
        end_index = min(length, math.ceil(visible_right / cw))

        sel_start = sel_end = None
        if self.selection_range is not None:
            sel_start, sel_end = self.selection_range

        # ---------------- LINE MODE ----------------
        if effective_mode == SequenceItemModel.LINE_MODE:
            total_width = length * cw
            visible_left = max(exposed.left(), 0.0)
            visible_right = min(exposed.right(), total_width)

            if visible_right > visible_left:
                line_h = self._model.line_height
                y = (ch - line_h) / 2.0
                painter.setBrush(self._LINE_BRUSH)
                painter.setPen(Qt.NoPen)
                painter.drawRect(
                    QRectF(visible_left, y, visible_right - visible_left, line_h)
                )

            painter.restore()
            return

        # ---------------- TEXT / BOX MODLARI ----------------

        # 1) Seçim arka planı (tek pass, sadece görünen indeksler)
        if sel_start is not None and sel_end is not None:
            sel_left_index = max(sel_start, start_index)
            sel_right_index = min(sel_end, end_index)
            if sel_right_index > sel_left_index:
                painter.setBrush(self._SELECTION_BRUSH)
                painter.setPen(Qt.NoPen)
                for i in range(sel_left_index, sel_right_index):
                    x = i * cw
                    painter.drawRect(QRectF(x, 0, cw, ch))

        # 2) TEXT_MODE: glyph cache + drawPixmap(QPointF)
        if effective_mode == SequenceItemModel.TEXT_MODE:
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.NoBrush)

            for i in range(start_index, end_index):
                base = seq[i]
                base_u = seq_upper[i]
                x = i * cw

                color = color_map.get(base_u, QColor(50, 50, 50))
                glyph = GLYPH_CACHE.get_glyph(base, self.font, color)

                gw = glyph.width()
                gh = glyph.height()

                dx = x + (cw - gw) / 2.0
                dy = (ch - gh) / 2.0

                painter.drawPixmap(QPointF(dx, dy), glyph)

        # 3) BOX_MODE: renkli kutucuk
        elif effective_mode == SequenceItemModel.BOX_MODE:
            painter.setPen(Qt.NoPen)
            box_h = self._model.box_height
            y = (ch - box_h) / 2.0
            for i in range(start_index, end_index):
                base_u = seq_upper[i]
                x = i * cw
                color = color_map.get(base_u, QColor(50, 50, 50))
                painter.setBrush(color)
                painter.drawRect(QRectF(x, y, cw, box_h))

        painter.restore()
