# features/navigation_ruler/navigation_ruler_widget.py

from typing import Optional

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QScrollBar

from features.sequence_viewer.sequence_viewer_widget import SequenceViewerWidget
from features.navigation_ruler.navigation_ruler_model import NavigationRulerModel
from settings.theme import theme_manager


class RulerWidget(QWidget):
    """Navigation Ruler (minimap). Dark-mode uyumlu."""

    def __init__(self, viewer: SequenceViewerWidget, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.viewer = viewer
        self.setMinimumHeight(28)
        self.setMaximumHeight(28)
        self.font = QFont("Arial", 8)
        self._model = NavigationRulerModel()

        hbar: QScrollBar = self.viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self._on_view_changed)
        hbar.rangeChanged.connect(self._on_view_changed)

        self._dragging_window = False
        self._drag_start_x    = 0
        self._drag_start_nt   = 0.0
        self._drag_last_nt    = 0.0
        self._drag_threshold_px = 3

        self._ruler_pixmap:   Optional[QPixmap] = None
        self._pixmap_max_len: int = 0
        self._pixmap_theme:   str = ""   # tema adı — tema değişince cache geçersiz

        # Tema değişince pixmap cache'i temizle + yeniden çiz
        theme_manager.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self, _theme) -> None:
        self._ruler_pixmap  = None
        self._pixmap_theme  = ""
        self.update()

    def _invalidate_ruler_pixmap(self) -> None:
        self._ruler_pixmap  = None
        self._pixmap_max_len = 0
        self._pixmap_theme   = ""
        self.update()

    def _rebuild_ruler_pixmap(self, width: int, height: int) -> None:
        max_len = self._model.cached_max_len
        if width <= 0 or height <= 0 or max_len <= 0:
            self._ruler_pixmap = None
            return

        layout = self._model.compute_tick_layout(width)
        if layout is None or layout.max_len <= 0:
            self._ruler_pixmap = None
            return

        max_len = layout.max_len
        t = theme_manager.current   # ← tema tokenları

        pm = QPixmap(width, height)
        pm.fill(t.ruler_bg)

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        # Çerçeve
        p.setPen(QPen(t.ruler_border))
        p.drawRect(QRectF(0, 0, width, height).adjusted(0, 0, -1, -1))

        p.setFont(self.font)
        p.setPen(QPen(t.ruler_fg))

        baseline_y       = height - 1
        tick_h_major     = 8
        tick_h_minor     = 4
        label_box_width  = 60.0

        for nt in layout.minor_ticks:
            x = int(nt / max_len * width)
            p.drawLine(x, baseline_y, x, baseline_y - tick_h_minor)

        for tick in layout.major_ticks:
            x = int(tick / max_len * width)
            p.drawLine(x, baseline_y, x, baseline_y - tick_h_major)

            display_value = 1 if tick == 0 else tick
            text = self._model.format_label(display_value)

            if tick == 0:
                text_rect = QRectF(0, 0, label_box_width, height - tick_h_major)
                align = Qt.AlignLeft | Qt.AlignVCenter
            elif tick == max_len:
                text_rect = QRectF(width - label_box_width, 0,
                                   label_box_width, height - tick_h_major)
                align = Qt.AlignRight | Qt.AlignVCenter
            else:
                text_rect = QRectF(x - label_box_width / 2.0, 0,
                                   label_box_width, height - tick_h_major)
                align = Qt.AlignHCenter | Qt.AlignVCenter

            p.drawText(text_rect, align, text)

        p.end()
        self._ruler_pixmap = pm

    def _on_view_changed(self, *_args) -> None:
        self.update()

    def _x_to_nt(self, x: int) -> float:
        self._model.recompute_max_len_if_needed(self.viewer.sequence_items)
        return self._model.x_to_nt(x, self.rect().width())

    def resizeEvent(self, event) -> None:
        self._invalidate_ruler_pixmap()
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        rect   = self.rect()
        width  = rect.width()
        height = self.height()
        t      = theme_manager.current

        max_len = self._model.recompute_max_len_if_needed(self.viewer.sequence_items)
        if max_len <= 0 or width <= 0:
            painter.fillRect(rect, QBrush(t.ruler_bg))
            painter.setPen(QPen(t.ruler_border))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            painter.end()
            return

        # Pixmap yeniden üret: boyut, max_len veya tema değişince
        if (self._ruler_pixmap is None
                or self._ruler_pixmap.width()  != width
                or self._ruler_pixmap.height() != height
                or self._pixmap_max_len        != max_len
                or self._pixmap_theme          != t.name):
            self._rebuild_ruler_pixmap(width, height)
            self._pixmap_max_len = max_len
            self._pixmap_theme   = t.name

        if self._ruler_pixmap is not None:
            painter.drawPixmap(0, 0, self._ruler_pixmap)
        else:
            painter.fillRect(rect, QBrush(t.ruler_bg))
            painter.setPen(QPen(t.ruler_border))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))

        # Yeşil viewport penceresi
        scene_rect = self.viewer.scene.sceneRect()
        scene_width = scene_rect.width()
        if scene_width > 0:
            hbar: QScrollBar = self.viewer.horizontalScrollBar()
            view_left  = float(hbar.value())
            view_width = float(self.viewer.viewport().width())
            view_right = view_left + view_width
            if scene_width <= view_width:
                x1, x2 = 0, width
            else:
                x1 = int(max(0.0, (view_left  / scene_width) * width))
                x2 = int(min(width, (view_right / scene_width) * width))
            if x2 > x1:
                painter.setBrush(QBrush(QColor(0, 200, 0, 60)))
                painter.setPen(QPen(QColor(0, 150, 0)))
                painter.drawRect(QRectF(x1, 1, x2 - x1, height - 2))

        # Drag seçim dikdörtgeni
        if self._dragging_window and max_len > 0:
            a = max(0.0, min(self._drag_start_nt, self._drag_last_nt))
            b = min(float(max_len), max(self._drag_start_nt, self._drag_last_nt))
            if b > a:
                x1 = int(a / max_len * width)
                x2 = int(b / max_len * width)
                if x2 > x1 + 2:
                    painter.setBrush(QBrush(QColor(0, 0, 255, 40)))
                    painter.setPen(QPen(QColor(0, 0, 160)))
                    painter.drawRect(QRectF(x1, 1, x2 - x1, height - 2))

        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            self._dragging_window = False
            self._drag_start_x  = x
            self._drag_start_nt = self._x_to_nt(x)
            self._drag_last_nt  = self._drag_start_nt
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton:
            x = event.pos().x()
            current_nt = self._x_to_nt(x)
            if not self._dragging_window:
                if abs(x - self._drag_start_x) >= self._drag_threshold_px:
                    self._dragging_window = True
            if self._dragging_window:
                self._drag_last_nt = current_nt
                self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            if self._dragging_window:
                current_nt = self._x_to_nt(x)
                self._drag_last_nt = current_nt
                self.viewer.zoom_to_nt_range(self._drag_start_nt, self._drag_last_nt)
            else:
                target_nt  = self._x_to_nt(x)
                hbar       = self.viewer.horizontalScrollBar()
                vp_width   = float(self.viewer.viewport().width())
                center_x   = target_nt * self.viewer.char_width
                new_left   = max(float(hbar.minimum()),
                                 min(center_x - vp_width / 2.0, float(hbar.maximum())))
                hbar.setValue(int(new_left))
            self._dragging_window = False
            self.update()
            event.accept()
        else:
            super().mouseReleaseEvent(event)