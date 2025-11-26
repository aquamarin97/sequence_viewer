from typing import Optional, Tuple, Dict

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter,
    QFont,
    QColor,
    QPen,
    QBrush,
    QPixmap,
    QFontMetrics,
)
from PyQt5.QtWidgets import QGraphicsItem
import math

def default_nucleotide_color_map() -> dict:
    return {
        "A": QColor(0, 180, 0),
        "T": QColor(200, 0, 0),
        "U": QColor(200, 0, 0),
        "C": QColor(0, 0, 200),
        "G": QColor(230, 140, 0),
        "-": QColor(150, 150, 150),
        "N": QColor(120, 120, 120),
    }


# ---------------- Glyph Cache ----------------


class _GlyphCache:
    """
    TEXT_MODE için harfleri pixmap olarak cache'ler.

    Key: (char, font_family, font_point_size_int, bold, italic, r, g, b)
    Val: QPixmap (harfin tight bounding box'ına göre çizilmiş hali)
    """

    def __init__(self) -> None:
        self._cache: Dict[Tuple, QPixmap] = {}

    def get_glyph(self, ch: str, font: QFont, color: QColor) -> QPixmap:
        key = (
            ch,
            font.family(),
            int(round(font.pointSizeF() or font.pointSize())),
            font.bold(),
            font.italic(),
            color.red(),
            color.green(),
            color.blue(),
        )
        pm = self._cache.get(key)
        if pm is not None:
            return pm

        metrics = QFontMetrics(font)
        w = max(1, metrics.horizontalAdvance(ch))
        h = max(1, metrics.height())

        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)

        p = QPainter(pm)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        p.setFont(font)
        p.setPen(QPen(color))
        p.drawText(0, metrics.ascent(), ch)
        p.end()

        self._cache[key] = pm
        return pm


_GLYPH_CACHE = _GlyphCache()


class SequenceGraphicsItem(QGraphicsItem):
    """
    Tek bir sekans satırı: sadece nt hücrelerini çizer (header yok).
    Zoom davranışı Geneious benzeri: satır yüksekliği sabit,
    zoom-in'de font sabit, hücreler genişler; zoom-out'ta font küçülür,
    BOX ve LINE moda geçilir.

    TEXT_MODE'da drawText() yerine glyph cache + drawPixmap() kullanır.
    """

    TEXT_MODE = "text"
    BOX_MODE = "box"
    LINE_MODE = "line"

    _BACKGROUND_BRUSH = QBrush(Qt.white)
    _LINE_BRUSH = QBrush(QColor(160, 160, 160))
    _SELECTION_BRUSH = QBrush(QColor(173, 216, 230))

    _TEXT_BOX_THRESHOLD = 8.0
    _BOX_LINE_THRESHOLD = 5.0

    def __init__(
        self,
        sequence: str,
        char_width: float = 12.0,
        char_height: float = 18.0,
        color_map: Optional[dict] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)

        # 🔹 Viewport-aware painting için ZORUNLU:
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption, True)

        self.sequence = sequence
        self.sequence_upper = sequence.upper()
        self.length = len(sequence)

        self.char_width = max(char_width, 0.001)
        self.char_height = max(1, int(round(char_height)))
        self.color_map = color_map or default_nucleotide_color_map()

        self.default_char_width = self.char_width

        self.selection_range: Optional[Tuple[int, int]] = None

        self.font = QFont("Courier New")
        self.font.setStyleHint(QFont.Monospace)
        self.font.setFixedPitch(True)

        self.base_font_size = self.char_height * 0.6
        self.display_mode: str = self.TEXT_MODE
        self.current_font_size: float = self.base_font_size
        self.box_height: float = self.char_height * 0.7
        self.line_height: float = self.char_height * 0.3

        self._lod_max_mode: Optional[str] = None

        self._update_font_and_mode()

    # ---------------- Public API ----------------

    def set_char_width(self, new_width: float) -> None:
        if new_width <= 0:
            new_width = 0.001
        if abs(new_width - self.char_width) < 0.0001:
            return
        self.prepareGeometryChange()
        self.char_width = new_width
        self._update_font_and_mode()

    def set_selection(self, start_col: int, end_col: int) -> None:
        start = max(0, min(start_col, end_col))
        end = min(self.length, max(start_col, end_col) + 1)
        if start >= end:
            self.selection_range = None
        else:
            self.selection_range = (start, end)
        self.update()

    def clear_selection(self) -> None:
        if self.selection_range is not None:
            self.selection_range = None
            self.update()

    def _update_font_and_mode(self) -> None:
        """
        Zoom'a göre font boyutu ve display mode'unu günceller.
        Font boyutu gerçekten değişmedikçe self.font.setPointSizeF çağrılmaz.
        Bu, animasyon sırasında saniyede 60+ kez gereksiz font engine yükünü önler.
        """
        if self.default_char_width <= 0:
            self.default_char_width = 12.0

        cw = max(self.char_width, 0.001)
        base_cw = max(self.default_char_width, 0.001)
        scale = cw / base_cw

        # ------------------- Font boyutu kademelendirme -------------------
        if scale >= 1.8:
            snapped_size = 12.0
        elif scale >= 1.2:
            snapped_size = 10.0
        elif scale >= 0.7:
            snapped_size = 8.0
        else:
            # 8pt altı lineer ölçekleme (BOX ve LINE modunda küçük geçişler için)
            snapped_size = max(1.0, self.base_font_size * scale)

        # ------------------- KRİTİK OPTİMİZASYON -------------------
        # Font boyutu gerçekten değiştiyse YALNIZCA o zaman güncelle
        if abs(self.current_font_size - snapped_size) >= 0.001:
            self.current_font_size = snapped_size
            self.font.setPointSizeF(snapped_size)
            # Font değiştiği için metrikler de değişebilir → geometry etkilenebilir
            self._font_metrics = None  # cache'i sıfırla (eğer varsa)
            self.prepareGeometryChange()  # sadece font değiştiğinde ekstra çağrı

        # ------------------- Display Mode Seçimi -------------------
        # Bu kısım her zaman çalışmalı çünkü mode değişimi geometry'i etkileyebilir
        old_mode = self.display_mode

        if self.current_font_size >= self._TEXT_BOX_THRESHOLD:  # >= 8.0
            self.display_mode = self.TEXT_MODE
        elif self.current_font_size >= self._BOX_LINE_THRESHOLD:  # >= 5.0
            self.display_mode = self.BOX_MODE
        else:
            self.display_mode = self.LINE_MODE

        # Mode değiştiyse geometry değişir → prepareGeometryChange gerekli
        if self.display_mode != old_mode:
            self.prepareGeometryChange()

        # ------------------- Kutucuk ve çizgi boyutları -------------------
        # current_font_size zaten güncel, direkt kullan
        box_reference_height = min(self.char_height * 0.7, self.current_font_size)
        self.box_height = max(box_reference_height, 1.0)
        self.line_height = self.char_height * 0.3

        # Not: char_width değiştiyse set_char_width zaten prepareGeometryChange() çağırıyordur.
        # Burada sadece font veya mode değiştiğinde ekstra çağırıyoruz.

    # ---------------- LOD override ----------------

    @staticmethod
    def _mode_order(mode: str) -> int:
        if mode == SequenceGraphicsItem.TEXT_MODE:
            return 0
        if mode == SequenceGraphicsItem.BOX_MODE:
            return 1
        return 2  # LINE_MODE

    def set_lod_max_mode(self, mode: Optional[str]) -> None:
        if mode not in (None, self.TEXT_MODE, self.BOX_MODE, self.LINE_MODE):
            return
        if mode == self._lod_max_mode:
            return
        self._lod_max_mode = mode
        self.update()

    # ---------------- QGraphicsItem interface ----------------

    def boundingRect(self) -> QRectF:
        width = self.char_width * self.length
        height = self.char_height
        return QRectF(0, 0, width, height)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        # 🔹 Viewport-aware: sadece gerçekten boyanan bölge için çalış
        if option is None or option.exposedRect.isNull():
            return

        painter.save()
        painter.setFont(self.font)

        exposed = option.exposedRect  # Qt bize sadece "kirli" alanı verir

        # Zoom + font’tan gelen mod:
        base_mode = self.display_mode
        if self._lod_max_mode is not None:
            if self._mode_order(base_mode) < self._mode_order(self._lod_max_mode):
                effective_mode = self._lod_max_mode
            else:
                effective_mode = base_mode
        else:
            effective_mode = base_mode

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
        if effective_mode == self.LINE_MODE:
            total_width = length * cw

            # exposedRect'ten sadece bu item'in kendi genişliği kadar kullan
            visible_left = max(exposed.left(), 0.0)
            visible_right = min(exposed.right(), total_width)

            if visible_right > visible_left:
                line_h = self.line_height
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
        if effective_mode == self.TEXT_MODE:
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.NoBrush)

            for i in range(start_index, end_index):
                base = seq[i]
                base_u = seq_upper[i]
                x = i * cw

                color = color_map.get(base_u, QColor(50, 50, 50))
                glyph = _GLYPH_CACHE.get_glyph(base, self.font, color)

                gw = glyph.width()
                gh = glyph.height()

                dx = x + (cw - gw) / 2.0
                dy = (ch - gh) / 2.0

                painter.drawPixmap(QPointF(dx, dy), glyph)

        # 3) BOX_MODE: renkli kutucuk
        elif effective_mode == self.BOX_MODE:
            painter.setPen(Qt.NoPen)
            box_h = self.box_height
            y = (ch - box_h) / 2.0
            for i in range(start_index, end_index):
                base_u = seq_upper[i]
                x = i * cw
                color = color_map.get(base_u, QColor(50, 50, 50))
                painter.setBrush(color)
                painter.drawRect(QRectF(x, y, cw, box_h))

        painter.restore()
