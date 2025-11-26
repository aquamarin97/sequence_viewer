# msa_viewer/widgets/navigation_ruler.py

from typing import Optional
import math

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QScrollBar

from .sequence_viewer import SequenceViewerWidget


class RulerWidget(QWidget):
    """
    En uzun diziye göre ölçeklenmiş, zoom/minimap benzeri cetvel (Navigation Ruler).

    Performans için:
    - Tick + label'lar bir QPixmap'e cache'lenir
    - Pixmap sadece:
        * en uzun dizi değiştiğinde
        * veya widget yeniden boyutlandığında
      yeniden üretilir.
    - Scroll/zoom sırasında sadece yeşil viewport dikdörtgeni yeniden çizilir.
    """

    def __init__(
        self,
        viewer: SequenceViewerWidget,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.viewer = viewer

        self.setMinimumHeight(28)
        self.setMaximumHeight(28)

        self.font = QFont("Arial", 8)

        # Viewer'ın scroll hareketlerini dinleyerek pencereyi güncelle
        hbar: QScrollBar = self.viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self._on_view_changed)
        hbar.rangeChanged.connect(self._on_view_changed)

        # Drag-select için durum
        self._dragging_window = False
        self._drag_start_x = 0
        self._drag_start_nt = 0.0
        self._drag_last_nt = 0.0
        self._drag_threshold_px = 3  # 3px üstü hareketi drag kabul et

        # ---- Performans cache'leri ----
        self._cached_max_len: int = 0
        self._last_seq_count: int = 0

        self._ruler_pixmap: Optional[QPixmap] = None

    # ------------------------------------------------------------------ #
    # Yardımcı fonksiyonlar
    # ------------------------------------------------------------------ 

    def _recompute_max_len_if_needed(self) -> int:
        """
        En uzun dizi uzunluğunu cache'ler.
        Sadece sequence satır sayısı değiştiğinde yeniden hesaplanır.
        En uzun diziyi cache'ler.
        Satır sayısı veya dizi uzunlukları değiştiğinde cache invalid edilir.
        """
        seq_count = len(self.viewer.sequence_items)
        new_max_len = max(
            (len(it.sequence) for it in self.viewer.sequence_items),
            default=0,
        )

        if seq_count != self._last_seq_count or new_max_len != self._cached_max_len:
            self._last_seq_count = seq_count
            self._cached_max_len = new_max_len
            self._invalidate_ruler_pixmap()

        return self._cached_max_len



    @staticmethod
    def _nice_tick_step(max_nt: int, pixel_width: int, target_px: int = 60) -> int:
        """
        Ölçeklenen cetvel için "güzel" (1,2,5 x 10^k) aralıklı tick step seçer.
        """
        if max_nt <= 0 or pixel_width <= 0:
            return max_nt if max_nt > 0 else 1

        raw_step = (max_nt * target_px) / float(pixel_width)
        if raw_step <= 0:
            return 1

        power = 10 ** int(math.floor(math.log10(raw_step)))
        base = raw_step / power

        if base <= 1:
            nice = 1
        elif base <= 2:
            nice = 2
        elif base <= 5:
            nice = 5
        else:
            nice = 10

        return int(nice * power)

    def _x_to_nt(self, x: int) -> float:
        """
        Cetvel üzerindeki piksel konumunu nt indeksine dönüştür.
        """
        max_len = self._recompute_max_len_if_needed()
        width = float(self.rect().width())
        if max_len <= 0 or width <= 0:
            return 0.0
        ratio = min(max(x / width, 0.0), 1.0)
        return ratio * max_len

    def _format_label(self, value: int, max_len: int) -> str:
        """
        Cetvel üzerindeki sayıları yazarken kullanılacak format.
        - max_len <= 1_000_000: normal sayı (örn. 5050)
        - max_len  > 1_000_000: K'li gösterim (örn. 10K, 250K)
        İlk label 1 ise her zaman '1' yazılır.
        """
        if value == 1:
            return "1"

        if max_len > 1_000_000:
            k_val = int(round(value / 1000.0))
            return f"{k_val}K"

        return str(value)

    def _invalidate_ruler_pixmap(self) -> None:
        """Tick/label pixmap'ini geçersiz kılar (bir sonraki paint'te yeniden üretilecek)."""
        self._ruler_pixmap = None
        self.update()

    def _rebuild_ruler_pixmap(self, width: int, height: int, max_len: int) -> None:
        """
        Tüm tick'leri ve label'ları bir QPixmap'e çizer.
        Yeşil viewport dikdörtgeni bu pixmap'e dahil edilmez; overlay olarak çizilir.
        """
        if width <= 0 or height <= 0 or max_len <= 0:
            self._ruler_pixmap = None
            return

        pm = QPixmap(width, height)
        pm.fill(Qt.white)

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        rect = QRectF(0, 0, width, height)

        # Çerçeve
        p.setPen(QPen(Qt.black))
        p.drawRect(rect.adjusted(0, 0, -1, -1))

        # Tick step
        tick_step = self._nice_tick_step(max_len, width)

        p.setFont(self.font)
        tick_pen = QPen(Qt.black)
        p.setPen(tick_pen)

        baseline_y = height - 1
        tick_height_major = 8
        tick_height_minor = 4

        # Minor ticks
        minor_step = max(tick_step // 5, 1)
        nt = 0
        while nt <= max_len:
            x = int(nt / max_len * width)
            p.drawLine(
                x, baseline_y,
                x, baseline_y - tick_height_minor
            )
            nt += minor_step

        # Major ticks listesi
        ticks = []
        nt = 0
        while nt <= max_len:
            ticks.append(nt)
            nt += tick_step

        last_nt = ticks[-1]
        delta = max_len - last_nt
        if delta != 0:
            if delta < tick_step * 0.5:
                ticks[-1] = max_len
            else:
                ticks.append(max_len)

        label_box_width = 60.0

        for t in ticks:
            x = int(t / max_len * width)

            # Tick çizgisi
            p.drawLine(
                x, baseline_y,
                x, baseline_y - tick_height_major
            )

            display_value = 1 if t == 0 else t
            text = self._format_label(display_value, max_len)

            if t == 0:
                text_rect = QRectF(
                    0,
                    0,
                    label_box_width,
                    height - tick_height_major,
                )
                align = Qt.AlignLeft | Qt.AlignVCenter
            elif t == max_len:
                text_rect = QRectF(
                    width - label_box_width,
                    0,
                    label_box_width,
                    height - tick_height_major,
                )
                align = Qt.AlignRight | Qt.AlignVCenter
            else:
                text_rect = QRectF(
                    x - label_box_width / 2.0,
                    0,
                    label_box_width,
                    height - tick_height_major,
                )
                align = Qt.AlignHCenter | Qt.AlignVCenter

            p.drawText(text_rect, align, text)

        p.end()
        self._ruler_pixmap = pm

    def _on_view_changed(self, *_args) -> None:
        # Scroll/zoom değişti → sadece viewport overlay'i güncelle
        self.update()

    # ------------------------------------------------------------------ #
    # Olaylar
    # ------------------------------------------------------------------ #

    def resizeEvent(self, event) -> None:
        # Boyut değişince cache'i invalid et
        self._invalidate_ruler_pixmap()
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        rect = self.rect()
        width = rect.width()
        height = self.height()

        max_len = self._recompute_max_len_if_needed()
        if max_len <= 0 or width <= 0:
            painter.fillRect(rect, QBrush(Qt.white))
            painter.setPen(QPen(Qt.black))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            painter.end()
            return

        # Gerekirse pixmap'i yeniden üret
        if (
            self._ruler_pixmap is None
            or self._ruler_pixmap.width() != width
            or self._ruler_pixmap.height() != height
        ):
            self._rebuild_ruler_pixmap(width, height, max_len)

        # Arkaplan + tick + label'lar: pixmap
        if self._ruler_pixmap is not None:
            painter.drawPixmap(0, 0, self._ruler_pixmap)
        else:
            painter.fillRect(rect, QBrush(Qt.white))
            painter.setPen(QPen(Qt.black))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))

        # ---- 1) Yeşil window (viewer viewport'ü) ----
        scene_rect = self.viewer.scene.sceneRect()
        scene_width = scene_rect.width()
        if scene_width > 0:
            hbar: QScrollBar = self.viewer.horizontalScrollBar()
            view_left = float(hbar.value())
            view_width = float(self.viewer.viewport().width())
            view_right = view_left + view_width

            if scene_width <= view_width:
                x1 = 0
                x2 = width
            else:
                x1 = int(max(0.0, (view_left / scene_width) * width))
                x2 = int(min(width, (view_right / scene_width) * width))

            if x2 > x1:
                painter.setBrush(QBrush(QColor(0, 200, 0, 60)))  # yarı saydam yeşil
                painter.setPen(QPen(QColor(0, 150, 0)))
                painter.drawRect(QRectF(x1, 1, x2 - x1, height - 2))

        # ---- 2) Drag sırasında seçim dikdörtgeni (zoom rectangle) ----
        if self._dragging_window and max_len > 0:
            w = float(width)
            a = max(0.0, min(self._drag_start_nt, self._drag_last_nt))
            b = min(float(max_len), max(self._drag_start_nt, self._drag_last_nt))

            if b > a:
                x1 = int(a / max_len * w)
                x2 = int(b / max_len * w)

                if x2 > x1 + 2:
                    painter.setBrush(QBrush(QColor(0, 0, 255, 40)))  # yarı saydam mavi
                    painter.setPen(QPen(QColor(0, 0, 160)))
                    painter.drawRect(QRectF(x1, 1, x2 - x1, height - 2))

        painter.end()

    # ------------------------------------------------------------------ #
    # Mouse interaction (değişmedi)
    # ------------------------------------------------------------------ #

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            self._dragging_window = False
            self._drag_start_x = x
            self._drag_start_nt = self._x_to_nt(x)
            self._drag_last_nt = self._drag_start_nt
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton:
            x = event.pos().x()
            current_nt = self._x_to_nt(x)

            # Drag mi yoksa küçük hareket mi?
            if not self._dragging_window:
                if abs(x - self._drag_start_x) >= self._drag_threshold_px:
                    self._dragging_window = True

            if self._dragging_window:
                # Sadece seçim dikdörtgenini güncelle, zoom YAPMA
                self._drag_last_nt = current_nt
                self.update()   # repaint → seçim rect'i yeniden çizilir

            event.accept()
        else:
            super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            x = event.pos().x()

            if self._dragging_window:
                # Drag bitti → seçilen aralığa tek seferde zoom yap
                current_nt = self._x_to_nt(x)
                self._drag_last_nt = current_nt

                # start ve end aynı ise, tek noktaya yakın zoom yapılır (senin zoom_to_nt_range zaten handle ediyor)
                self.viewer.zoom_to_nt_range(
                    self._drag_start_nt,
                    self._drag_last_nt,
                )
            else:
                # Drag olmazsa: sadece tıklama → o nt'yi merkeze al
                target_nt = self._x_to_nt(x)
                hbar = self.viewer.horizontalScrollBar()
                viewport_width = float(self.viewer.viewport().width())

                center_x = target_nt * self.viewer.char_width
                new_left = center_x - viewport_width / 2.0

                new_left = max(
                    float(hbar.minimum()),
                    min(new_left, float(hbar.maximum())),
                )
                hbar.setValue(int(new_left))

            self._dragging_window = False
            self.update()  # seçim dikdörtgenini temizle
            event.accept()
        else:
            super().mouseReleaseEvent(event)
