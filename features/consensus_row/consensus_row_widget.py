# features/consensus_row/consensus_row_widget.py
"""
Konsensüs satırı widget'ı.

Özellikler
----------
* Position ruler'ın hemen altında, sabit (dikey scroll etkilemez).
* Yatay olarak SequenceViewer ile tam senkron (scroll + zoom animasyonu).
* Aynı LOD sistemi: TEXT / BOX / LINE (SequenceItemModel eşikleriyle uyumlu).
* Nükleotid renk haritası SequenceGraphicsItem ile aynı.
* Dark Mode: theme_manager.themeChanged sinyaline bağlı.
* AlignmentDataModel sinyallerine subscribe — veri değişince cache geçersiz.
"""

from __future__ import annotations

import math
from typing import Optional

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor,
    QFont, QFontMetrics,
)
from PyQt5.QtWidgets import QWidget, QScrollBar

from features.consensus_row.consensus_row_model import ConsensusRowModel
from graphics.sequence_item.sequence_glyph_cache import (
    default_nucleotide_color_map, GLYPH_CACHE,
)
from model.alignment_data_model import AlignmentDataModel
from model.consensus_calculator import ConsensusMethod
from settings.theme import theme_manager

# LOD eşikleri — SequenceItemModel ile aynı tutuldu
_TEXT_THRESHOLD = 8.0
_BOX_THRESHOLD  = 5.0

# Sabit yükseklik
_ROW_HEIGHT = 20


class ConsensusRowWidget(QWidget):
    """
    Hizalanmış dizilerden hesaplanan konsensüs satırını çizer.

    Parametreler
    ------------
    alignment_model : AlignmentDataModel
        Veri kaynağı. Sinyallerine subscribe olur.
    sequence_viewer : SequenceViewerWidget
        Yatay scroll ve char_width senkronizasyonu için referans.
    """

    def __init__(
        self,
        alignment_model: AlignmentDataModel,
        sequence_viewer,                      # SequenceViewerWidget — tip döngüsü önlemek için str hint yok
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._alignment_model = alignment_model
        self._sequence_viewer = sequence_viewer
        self._initial_char_width = float(sequence_viewer.char_width)  # ← ekle

        # Model
        self._model = ConsensusRowModel(method=ConsensusMethod.PLURALITY)

        # Font
        self._font = QFont("Courier New")
        self._font.setStyleHint(QFont.Monospace)
        self._font.setFixedPitch(True)

        # Renk haritası
        self._color_map = default_nucleotide_color_map()

        # Boyut
        self.setFixedHeight(_ROW_HEIGHT)
        self.setMinimumWidth(0)

        # AlignmentDataModel sinyalleri → cache geçersiz + repaint
        self._alignment_model.rowAppended.connect(self._on_data_changed)
        self._alignment_model.rowRemoved.connect(self._on_data_changed)
        self._alignment_model.rowMoved.connect(self._on_data_changed)
        self._alignment_model.modelReset.connect(self._on_data_changed)
        # headerChanged konsensüsü etkilemez — bağlanmıyor


        # SequenceViewer scroll + zoom senkronizasyonu
        hbar: QScrollBar = self._sequence_viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self.update)
        hbar.rangeChanged.connect(self.update)

        # Zoom animasyonu: SequenceViewerView'da _zoom_animation var
        anim = getattr(self._sequence_viewer, "_zoom_animation", None)
        if anim is not None:
            anim.valueChanged.connect(self.update)

        # Tema değişince repaint
        theme_manager.themeChanged.connect(self._on_theme_changed)

    # ------------------------------------------------------------------
    # Ayar API'si (dışarıdan çağrılabilir — toolbar, menü vb.)
    # ------------------------------------------------------------------

    def set_method(
        self,
        method: ConsensusMethod,
        threshold: Optional[float] = None,
    ) -> None:
        """
        Hesaplama yöntemini değiştirir.
        Cache otomatik geçersiz olur, widget yeniden çizilir.
        """
        self._model.set_method(method, threshold)
        self.update()

    @property
    def current_method(self) -> ConsensusMethod:
        return self._model.method

    @property
    def current_threshold(self) -> float:
        return self._model.threshold

    # ------------------------------------------------------------------
    # Slot'lar
    # ------------------------------------------------------------------

    def _on_data_changed(self, *_args) -> None:
        self._model.invalidate()
        self.update()

    def _on_theme_changed(self, _theme) -> None:
        self.update()

    # ------------------------------------------------------------------
    # Çizim yardımcıları
    # ------------------------------------------------------------------

    def _get_char_width(self) -> float:
        """Zoom animasyonu sırasında ara değeri yakalar."""
        if hasattr(self._sequence_viewer, "_get_current_char_width"):
            return float(self._sequence_viewer._get_current_char_width())
        return float(self._sequence_viewer.char_width)

    def _get_view_left(self) -> float:
        """Yatay kaydırma offset'i (scene px)."""
        hbar = self._sequence_viewer.horizontalScrollBar()
        return float(hbar.value())

    def _effective_mode(self, char_width: float) -> str:
        """
        Modu doğrudan SequenceViewer'ın item'larından okur.
        Viewer zaten doğru hesaplamış — tekrar hesaplamaya gerek yok.
        Fallback: başlangıç char_width'ini referans alarak scale hesapla.
        """
        items = getattr(self._sequence_viewer, "sequence_items", None)
        if items:
            return items[0].display_mode   # "text" | "box" | "line"

        # Fallback — viewer henüz doldurulmamışsa
        cw_default = self._initial_char_width or 12.0
        scale      = char_width / cw_default

        if scale >= 1.8:   font_size = 12.0
        elif scale >= 1.2: font_size = 10.0
        elif scale >= 0.7: font_size = 8.0
        else:              font_size = max(1.0, 18.0 * 0.6 * scale)

        if font_size >= _TEXT_THRESHOLD: return "text"
        if font_size >= _BOX_THRESHOLD:  return "box"
        return "line"
    
    def _sync_font_size(self, char_width: float) -> None:
        cw_default = self._initial_char_width or 12.0
        scale      = char_width / cw_default

        if scale >= 1.8:   size = 12.0
        elif scale >= 1.2: size = 10.0
        elif scale >= 0.7: size = 8.0
        else:              size = max(1.0, 18.0 * 0.6 * scale)

        self._font.setPointSizeF(size)

    # ------------------------------------------------------------------
    # paintEvent
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        rect   = self.rect()
        width  = rect.width()
        height = rect.height()
        t      = theme_manager.current

        # --- Arkaplan ---
        # Consensus row için ayrı bir token kullanabiliriz;
        # şimdilik row_bg_odd (hafif tonlu) ile ayırt ediyoruz.
        bg = QColor(t.row_bg_odd)
        painter.fillRect(rect, QBrush(bg))

        # --- Etiket alanı: "Consensus" yazısı ---
        # Bu widget sadece sağ panelde (sequence viewer üstünde) yer alır,
        # sol panel (header) tarafı ayrı bir spacer widget'ı.

        # --- Alt çizgi ---
        painter.setPen(QPen(t.border_normal))
        painter.drawLine(0, height - 1, width, height - 1)

        # --- Sekans yoksa erken çık ---
        sequences = [seq for _, seq in self._alignment_model.all_rows()]
        if not sequences:
            painter.setPen(QPen(t.text_primary))
            painter.setFont(self._font)
            painter.drawText(rect.adjusted(6, 0, 0, 0),
                             Qt.AlignVCenter | Qt.AlignLeft, "—")
            painter.end()
            return

        # --- Konsensüs hesapla (cache) ---
        consensus = self._model.get_consensus(sequences)
        if not consensus:
            painter.end()
            return

        # --- Zoom / scroll durumu ---
        cw       = self._get_char_width()
        view_left = self._get_view_left()

        if cw <= 0:
            painter.end()
            return

        self._sync_font_size(cw)
        painter.setFont(self._font)

        mode   = self._effective_mode(cw)
        ch     = float(height)
        length = len(consensus)

        # Görünür kolon aralığı
        start_col = max(0, int(math.floor(view_left / cw)))
        end_col   = min(length, int(math.ceil((view_left + width) / cw)))

        # --- LINE modu ---
        if mode == "line":
            line_h = ch * 0.3
            y      = (ch - line_h) / 2.0

            # Sequence viewer ile aynı sınır: length * cw, ardından trailing_padding boş
            trailing_px = getattr(
                self._sequence_viewer, "trailing_padding_line_px", 80.0
            )
            seq_end_x  = length * cw - view_left
            draw_width = max(0.0, min(float(width), seq_end_x))

            painter.setBrush(QBrush(QColor(160, 160, 160)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(0, y, draw_width, line_h))
            painter.end()
            return

        # --- TEXT / BOX modları ---
        box_h = min(ch * 0.75, self._font.pointSizeF() * 1.4)
        box_y = (ch - box_h) / 2.0

        for col in range(start_col, end_col):
            base = consensus[col].upper()
            x    = col * cw - view_left

            color = self._color_map.get(base, QColor(80, 80, 80))

            if mode == "box":
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)
                painter.drawRect(QRectF(x, box_y, cw, box_h))

            else:  # text
                glyph = GLYPH_CACHE.get_glyph(base, self._font, color)
                gw    = glyph.width()
                gh    = glyph.height()
                dx    = x + (cw - gw) / 2.0
                dy    = (ch - gh) / 2.0
                painter.drawPixmap(int(dx), int(dy), glyph)

        painter.end()