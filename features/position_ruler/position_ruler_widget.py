# features/position_ruler/position_ruler_widget.py

import math
from typing import Optional

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics
from PyQt5.QtWidgets import QWidget, QScrollBar

from features.sequence_viewer.sequence_viewer_widget import SequenceViewerWidget
from features.position_ruler.position_ruler_model import PositionRulerModel, PositionRulerLayout
from settings.theme import theme_manager


class SequencePositionRulerWidget(QWidget):
    """Sequence position cetveli. Dark-mode uyumlu."""

    def __init__(self, viewer: SequenceViewerWidget, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.viewer = viewer
        self.setMinimumHeight(24)
        self.setMaximumHeight(24)
        self.font = QFont("Arial", 8)
        self._model = PositionRulerModel()

        hbar: QScrollBar = self.viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self._on_view_changed)
        hbar.rangeChanged.connect(self._on_view_changed)
        self.viewer.selectionChanged.connect(self._on_view_changed)

        theme_manager.themeChanged.connect(self.update)

    def _on_view_changed(self, *_args) -> None:
        self.update()

    def _update_model_from_viewer(self) -> Optional[PositionRulerLayout]:
        max_len = getattr(self.viewer, "max_sequence_length", 0)
        if max_len <= 0 and getattr(self.viewer, "sequence_items", None):
            try:
                max_len = max(len(item.sequence) for item in self.viewer.sequence_items)
            except ValueError:
                max_len = 0

        view_scene_rect = self.viewer.mapToScene(
            self.viewer.viewport().rect()
        ).boundingRect()
        view_left  = float(view_scene_rect.left())
        view_width = float(view_scene_rect.width())

        if hasattr(self.viewer, "_get_current_char_width"):
            char_width = float(self.viewer._get_current_char_width())
        else:
            char_width = float(self.viewer.char_width)

        selection_cols = getattr(self.viewer, "current_selection_cols", None)

        self._model.set_state(
            max_len=max_len, view_left=view_left, view_width=view_width,
            char_width=char_width, selection_cols=selection_cols,
        )
        return self._model.compute_layout()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        rect   = self.rect()
        width  = rect.width()
        height = rect.height()
        t      = theme_manager.current   # ← tema tokenları

        painter.fillRect(rect, QBrush(t.ruler_bg))

        if width <= 0:
            painter.end()
            return

        layout = self._update_model_from_viewer()
        if layout is None or layout.max_len <= 0:
            painter.setPen(QPen(t.ruler_border))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            painter.end()
            return

        # Alt sınır çizgisi
        painter.setPen(QPen(t.ruler_border))
        painter.drawLine(rect.left(), rect.bottom() - 1, rect.right(), rect.bottom() - 1)

        char_width = self._model.char_width
        view_left  = self._model.view_left
        if char_width <= 0 or self._model.view_width <= 0:
            painter.end()
            return

        painter.setFont(self.font)
        metrics = QFontMetrics(self.font)

        first_pos         = layout.first_pos
        last_pos          = layout.last_pos
        step              = layout.step
        special_positions = list(layout.special_positions)

        baseline_y = height - 2
        tick_h     = 6
        normal_pen = QPen(t.ruler_fg)

        # ---- Seçim label rect'leri (çakışma kontrolü) ----
        selection_label_rects = []
        for pos in special_positions:
            if pos < first_pos or pos > last_pos:
                continue
            x = (pos - 0.5) * char_width - view_left
            if 0 <= x <= width:
                lw = metrics.horizontalAdvance(str(pos))
                r  = rect.adjusted(0, 0, 0, -4)
                r.setLeft(int(x - lw / 2))
                r.setRight(int(x + lw / 2))
                selection_label_rects.append(r)

        drawn_tick_rects = []

        def intersects_any(lst, cand):
            return any(r.intersects(cand) for r in lst)

        def can_draw_tick(cx):
            cand = rect.adjusted(0, 0, 0, -4)
            cand.setLeft(int(cx - 20))
            cand.setRight(int(cx + 20))
            if intersects_any(selection_label_rects, cand):
                return False
            if intersects_any(drawn_tick_rects, cand):
                return False
            drawn_tick_rects.append(cand)
            return True

        # ---- Pozisyon 1 ----
        if 1 >= first_pos and 1 <= last_pos:
            x = (1 - 0.5) * char_width - view_left
            if 0 <= x <= width:
                painter.setPen(normal_pen)
                painter.drawLine(int(x), baseline_y, int(x), baseline_y - tick_h)
                if can_draw_tick(x):
                    lw = metrics.horizontalAdvance("1")
                    r  = rect.adjusted(0, 0, 0, -4)
                    r.setLeft(int(x - lw / 2))
                    r.setRight(int(x + lw / 2))
                    painter.drawText(r, Qt.AlignHCenter | Qt.AlignTop, "1")

        # ---- Ana tick'ler ----
        start_pos = (((max(step, first_pos) + step - 1) // step) * step)
        pos = start_pos
        while pos <= last_pos:
            x = (pos - 0.5) * char_width - view_left
            if 0 <= x <= width:
                painter.setPen(normal_pen)
                painter.drawLine(int(x), baseline_y, int(x), baseline_y - tick_h)
                if can_draw_tick(x):
                    label = str(pos)
                    lw    = metrics.horizontalAdvance(label)
                    r     = rect.adjusted(0, 0, 0, -4)
                    r.setLeft(int(x - lw / 2))
                    r.setRight(int(x + lw / 2))
                    painter.drawText(r, Qt.AlignHCenter | Qt.AlignTop, label)
            pos += step

        # ---- Seçim pozisyonları (bold, vurgulu renk) ----
        if special_positions:
            bold_font = QFont(self.font)
            bold_font.setBold(True)
            painter.setFont(bold_font)
            painter.setPen(QPen(t.ruler_selection_fg))
            drawn_special = set()
            drawn_special_rects = []

            for pos in special_positions:
                if pos in drawn_special or pos < first_pos or pos > last_pos:
                    continue
                drawn_special.add(pos)
                x = (pos - 0.5) * char_width - view_left
                if x < 0 or x > width:
                    continue
                label = str(pos)
                lw    = metrics.horizontalAdvance(label)
                cand  = rect.adjusted(0, 0, 0, -4)
                cand.setLeft(int(x - lw / 2))
                cand.setRight(int(x + lw / 2))
                if intersects_any(drawn_special_rects, cand):
                    continue
                drawn_special_rects.append(cand)
                painter.drawText(cand, Qt.AlignHCenter | Qt.AlignTop, label)

        painter.end()