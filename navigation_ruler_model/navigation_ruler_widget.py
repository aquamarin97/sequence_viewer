# msa_viewer/navigation_ruler/navigation_ruler_widget.py

from typing import Optional

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QScrollBar

from sequence_viewer.sequence_viewer_widget import SequenceViewerWidget
from .navigation_ruler_model import NavigationRulerModel


class RulerWidget(QWidget):
    """
    En uzun diziye göre ölçeklenmiş, zoom/minimap benzeri cetvel (Navigation Ruler).

    CMV:
    - Model : NavigationRulerModel (max_len cache, tick layout, x→nt mapping)
    - View  : Bu QWidget (QPainter + pixmap cache)
    - Control: Mouse event'leri (drag-select, tıklamayla merkezleme) yine bu sınıfta.
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

        # Model
        self._model = NavigationRulerModel()

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
        self._ruler_pixmap: Optional[QPixmap] = None
        self._pixmap_max_len: int = 0  # pixmap üretilirken kullanılan max_len

    # ------------------------------------------------------------------ #
    # Yardımcı fonksiyonlar
    # ------------------------------------------------------------------ #

    def _invalidate_ruler_pixmap(self) -> None:
        """
        Tick/label pixmap'ini geçersiz kılar (bir sonraki paint'te yeniden üretilecek).
        """
        self._ruler_pixmap = None
        self._pixmap_max_len = 0
        self.update()

    def _rebuild_ruler_pixmap(self, width: int, height: int) -> None:
        """
        Tüm tick'leri ve label'ları bir QPixmap'e çizer.
        Yeşil viewport dikdörtgeni bu pixmap'e dahil edilmez; overlay olarak çizilir.
        """
        max_len = self._model.cached_max_len
        if width <= 0 or height <= 0 or max_len <= 0:
            self._ruler_pixmap = None
            return

        layout = self._model.compute_tick_layout(width)
        if layout is None or layout.max_len <= 0:
            self._ruler_pixmap = None
            return

        max_len = layout.max_len

        pm = QPixmap(width, height)
        pm.fill(Qt.white)

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        rect = QRectF(0, 0, width, height)

        # Çerçeve
        p.setPen(QPen(Qt.black))
        p.drawRect(rect.adjusted(0, 0, -1, -1))

        p.setFont(self.font)
        tick_pen = QPen(Qt.black)
        p.setPen(tick_pen)

        baseline_y = height - 1
        tick_height_major = 8
        tick_height_minor = 4

        # Minor ticks
        for nt in layout.minor_ticks:
            x = int(nt / max_len * width)
            p.drawLine(
                x,
                baseline_y,
                x,
                baseline_y - tick_height_minor,
            )

        # Major ticks
        label_box_width = 60.0

        for t in layout.major_ticks:
            x = int(t / max_len * width)

            # Tick çizgisi
            p.drawLine(
                x,
                baseline_y,
                x,
                baseline_y - tick_height_major,
            )

            display_value = 1 if t == 0 else t
            text = self._model.format_label(display_value)

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

    def _x_to_nt(self, x: int) -> float:
        """
        Mevcut viewer state'ine göre x pikselini nt değerine çevir.
        (Model'in cache'ini güncel tutarak)
        """
        self._model.recompute_max_len_if_needed(self.viewer.sequence_items)
        width = self.rect().width()
        return self._model.x_to_nt(x, width)

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

        max_len = self._model.recompute_max_len_if_needed(self.viewer.sequence_items)
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
            or self._pixmap_max_len != max_len
        ):
            self._rebuild_ruler_pixmap(width, height)
            self._pixmap_max_len = max_len

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
    # Mouse interaction
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

                # start ve end aynı ise, tek noktaya yakın zoom yapılır
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
