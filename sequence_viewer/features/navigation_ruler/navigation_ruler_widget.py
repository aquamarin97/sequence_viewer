# sequence_viewer/features/navigation_ruler/navigation_ruler_widget.py
# features/navigation_ruler/navigation_ruler_widget.py
from typing import Optional
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QScrollBar
from sequence_viewer.features.sequence_viewer.sequence_viewer_widget import SequenceViewerWidget
from sequence_viewer.features.navigation_ruler.navigation_ruler_model import NavigationRulerModel
from sequence_viewer.settings.mouse_binding_manager import mouse_binding_manager
from sequence_viewer.settings.theme import theme_manager

class RulerWidget(QWidget):
    def __init__(self, viewer, parent=None):
        super().__init__(parent); self.viewer = viewer
        self.setMinimumHeight(28); self.setMaximumHeight(28)
        self.font = QFont("Arial", 8); self._model = NavigationRulerModel()
        hbar = self.viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self._on_view_changed); hbar.rangeChanged.connect(self._on_view_changed)
        self._dragging_window = False; self._drag_start_x = 0
        self._drag_start_nt = 0.0; self._drag_last_nt = 0.0
        self._ruler_pixmap = None; self._pixmap_max_len = 0; self._pixmap_theme = ""
        theme_manager.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self, _): self._ruler_pixmap = None; self._pixmap_theme = ""; self.update()
    def _invalidate_ruler_pixmap(self): self._ruler_pixmap = None; self._pixmap_max_len = 0; self._pixmap_theme = ""; self.update()
    def _on_view_changed(self, *_): self.update()

    def _rebuild_ruler_pixmap(self, width, height):
        max_len = self._model.cached_max_len
        if width <= 0 or height <= 0 or max_len <= 0: self._ruler_pixmap = None; return
        layout = self._model.compute_tick_layout(width)
        if layout is None or layout.max_len <= 0: self._ruler_pixmap = None; return
        max_len = layout.max_len; t = theme_manager.current
        pm = QPixmap(width, height); pm.fill(t.nav_ruler_bg)
        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing, False); p.setRenderHint(QPainter.TextAntialiasing, True)
        p.setPen(QPen(t.ruler_border)); p.drawRect(QRectF(0,0,width,height).adjusted(0,0,-1,-1))
        p.setFont(self.font); p.setPen(QPen(t.ruler_fg))
        baseline_y = height-1
        for nt in layout.minor_ticks:
            x = int(nt/max_len*width); p.drawLine(x, baseline_y, x, baseline_y-4)
        for tick in layout.major_ticks:
            x = int(tick/max_len*width); p.drawLine(x, baseline_y, x, baseline_y-8)
            display_value = 1 if tick == 0 else tick; text = self._model.format_label(display_value)
            lbw = 60.0
            if tick == 0: tr = QRectF(0,0,lbw,height-8); al = Qt.AlignLeft|Qt.AlignVCenter
            elif tick == max_len: tr = QRectF(width-lbw,0,lbw,height-8); al = Qt.AlignRight|Qt.AlignVCenter
            else: tr = QRectF(x-lbw/2,0,lbw,height-8); al = Qt.AlignHCenter|Qt.AlignVCenter
            p.drawText(tr, al, text)
        p.end(); self._ruler_pixmap = pm

    def _x_to_nt(self, x):
        self._model.recompute_max_len_if_needed(self.viewer.sequence_items)
        return self._model.x_to_nt(x, self.rect().width())

    def resizeEvent(self, event): self._invalidate_ruler_pixmap(); super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self); rect = self.rect(); width = rect.width(); height = self.height()
        t = theme_manager.current
        max_len = self._model.recompute_max_len_if_needed(self.viewer.sequence_items)
        if max_len <= 0 or width <= 0:
            painter.fillRect(rect, QBrush(t.nav_ruler_bg)); painter.setPen(QPen(t.ruler_border))
            painter.drawRect(rect.adjusted(0,0,-1,-1)); painter.end(); return
        if (self._ruler_pixmap is None or self._ruler_pixmap.width() != width or self._ruler_pixmap.height() != height or self._pixmap_max_len != max_len or self._pixmap_theme != t.name):
            self._rebuild_ruler_pixmap(width, height); self._pixmap_max_len = max_len; self._pixmap_theme = t.name
        if self._ruler_pixmap: painter.drawPixmap(0,0,self._ruler_pixmap)
        else:
            painter.fillRect(rect, QBrush(t.nav_ruler_bg)); painter.setPen(QPen(t.ruler_border)); painter.drawRect(rect.adjusted(0,0,-1,-1))
        scene_rect = self.viewer.scene.sceneRect(); scene_width = scene_rect.width()
        if scene_width > 0:
            hbar = self.viewer.horizontalScrollBar(); view_left = float(hbar.value())
            view_width = float(self.viewer.viewport().width()); view_right = view_left + view_width
            if scene_width <= view_width: x1, x2 = 0, width
            else: x1 = int(max(0.0,(view_left/scene_width)*width)); x2 = int(min(width,(view_right/scene_width)*width))
            if x2 > x1:
                painter.setBrush(QBrush(t.nav_ruler_viewport_fill)); painter.setPen(QPen(t.nav_ruler_viewport_border))
                painter.drawRect(QRectF(x1,1,x2-x1,height-2))
        if self._dragging_window and max_len > 0:
            a = max(0.0, min(self._drag_start_nt, self._drag_last_nt))
            b = min(float(max_len), max(self._drag_start_nt, self._drag_last_nt))
            if b > a:
                x1 = int(a/max_len*width); x2 = int(b/max_len*width)
                if x2 > x1+2:
                    painter.setBrush(QBrush(t.nav_ruler_drag_fill)); painter.setPen(QPen(t.nav_ruler_drag_border))
                    painter.drawRect(QRectF(x1,1,x2-x1,height-2))
        painter.end()

    def mousePressEvent(self, event):
        if mouse_binding_manager.is_navigation_zoom_to_range_event(event.modifiers(), event.button()):
            x = event.pos().x(); self._dragging_window = False
            self._drag_start_x = x; self._drag_start_nt = self._x_to_nt(x); self._drag_last_nt = self._drag_start_nt
            event.accept()
        else: super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton and
                mouse_binding_manager.is_navigation_zoom_to_range_event(event.modifiers(), Qt.LeftButton)):
            x = event.pos().x(); current_nt = self._x_to_nt(x)
            if not self._dragging_window:
                if abs(x - self._drag_start_x) >= mouse_binding_manager.drag_threshold("navigation_ruler"):
                    self._dragging_window = True
            if self._dragging_window: self._drag_last_nt = current_nt; self.update()
            event.accept()
        else: super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            if self._dragging_window and mouse_binding_manager.is_navigation_zoom_to_range_event(event.modifiers(), event.button()):
                self._drag_last_nt = self._x_to_nt(x)
                self.viewer.zoom_to_nt_range(self._drag_start_nt, self._drag_last_nt)
            elif mouse_binding_manager.is_navigation_scroll_to_event(event.modifiers(), event.button()):
                target_nt = self._x_to_nt(x); hbar = self.viewer.horizontalScrollBar()
                vp_width = float(self.viewer.viewport().width())
                center_x = target_nt * self.viewer.char_width
                new_left = max(float(hbar.minimum()), min(center_x - vp_width/2.0, float(hbar.maximum())))
                hbar.setValue(int(new_left))
            else:
                self._dragging_window = False
                super().mouseReleaseEvent(event)
                return
            self._dragging_window = False; self.update(); event.accept()
        else: super().mouseReleaseEvent(event)


