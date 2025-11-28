# msa_viewer/position_ruler/position_ruler_widget.py

import math
from typing import Optional

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics
from PyQt5.QtWidgets import QWidget, QScrollBar

from sequence_viewer.sequence_viewer_widget import SequenceViewerWidget
from .position_ruler_model import PositionRulerModel, PositionRulerLayout


class SequencePositionRulerWidget(QWidget):
    """
    Sequence row'larının hemen üstünde duran ikinci ruler.

    CMV ayrımı:
    - Model : PositionRulerModel  (max_len, görünür aralık, step, seçim pozisyonları)
    - View  : Bu QWidget (QPainter ile çizim + SequenceViewer'dan state çekme)

    - Horizontal scroll + zoom ile senkron, ama kendisi scale edilmiyor.
    - Tick'ler zoom seviyesine göre seyrek/sık.
    - Seçilen nt veya nt-aralığının pozisyonlarını vurgular.
    """

    def __init__(
        self,
        viewer: SequenceViewerWidget,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.viewer = viewer

        self.setMinimumHeight(24)
        self.setMaximumHeight(24)

        self.font = QFont("Arial", 8)

        # Model
        self._model = PositionRulerModel()

        # Viewer event'lerine abone ol → repaint tetikle
        hbar: QScrollBar = self.viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self._on_view_changed)
        hbar.rangeChanged.connect(self._on_view_changed)
        self.viewer.selectionChanged.connect(self._on_view_changed)

    # ------------------------------------------------------------------
    # Viewer değişince yeniden çiz
    # ------------------------------------------------------------------

    def _on_view_changed(self, *_args) -> None:
        self.update()

    # ------------------------------------------------------------------
    # Model'i viewer state'inden besle
    # ------------------------------------------------------------------

    def _update_model_from_viewer(self) -> Optional[PositionRulerLayout]:
        """
        Viewer'ın o anki zoom/scroll/selection durumuna göre model state'ini günceller
        ve layout'u hesaplar.
        """
        # max sequence length: SequenceViewerView içinde cache'lenmiş durumda
        max_len = getattr(self.viewer, "max_sequence_length", 0)

        # Fallback: cache yoksa item'lardan hesapla
        if max_len <= 0 and getattr(self.viewer, "sequence_items", None):
            try:
                max_len = max(len(item.sequence) for item in self.viewer.sequence_items)
            except ValueError:
                max_len = 0

        view_scene_rect = self.viewer.mapToScene(
            self.viewer.viewport().rect()
        ).boundingRect()

        view_left = float(view_scene_rect.left())
        view_width = float(view_scene_rect.width())

        # Zoom animasyonundaki anlık değeri yakalamak için helper kullan
        if hasattr(self.viewer, "_get_current_char_width"):
            char_width = float(self.viewer._get_current_char_width())  # type: ignore[attr-defined]
        else:
            char_width = float(self.viewer.char_width)

        selection_cols = getattr(self.viewer, "current_selection_cols", None)

        self._model.set_state(
            max_len=max_len,
            view_left=view_left,
            view_width=view_width,
            char_width=char_width,
            selection_cols=selection_cols,
        )

        return self._model.compute_layout()

    # ------------------------------------------------------------------
    # Çizim
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        rect = self.rect()
        width = rect.width()
        height = rect.height()

        painter.fillRect(rect, QBrush(Qt.white))

        if width <= 0:
            painter.end()
            return

        layout = self._update_model_from_viewer()
        if layout is None or layout.max_len <= 0:
            # Sınır çiz, başka bir şey yok
            painter.setPen(QPen(Qt.black))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            painter.end()
            return

        # Alt sınır çizgisi
        painter.setPen(QPen(Qt.black))
        painter.drawLine(
            rect.left(), rect.bottom() - 1, rect.right(), rect.bottom() - 1
        )

        char_width = self._model.char_width
        view_left = self._model.view_left
        if char_width <= 0 or self._model.view_width <= 0:
            painter.end()
            return

        painter.setFont(self.font)
        metrics = QFontMetrics(self.font)

        first_pos = layout.first_pos
        last_pos = layout.last_pos
        step = layout.step
        sel_start_pos = layout.sel_start_pos
        sel_end_pos = layout.sel_end_pos
        special_positions = list(layout.special_positions)

        baseline_y = height - 2
        tick_h = 6

        normal_pen = QPen(QColor(0, 0, 0))
        painter.setPen(normal_pen)

        # --------------------------------------------------------------
        # Seçili pozisyonlar için label rect'leri (tick label çakışma kontrolü)
        # --------------------------------------------------------------
        selection_label_rects = []

        for pos in special_positions:
            if pos < first_pos or pos > last_pos:
                continue

            center_scene_x = (pos - 0.5) * char_width
            x = center_scene_x - view_left
            if 0 <= x <= width:
                label_text = str(pos)
                text_width = metrics.horizontalAdvance(label_text)
                half_w = text_width / 2.0

                text_rect = rect.adjusted(0, 0, 0, -4)
                text_rect.setLeft(int(x - half_w))
                text_rect.setRight(int(x + half_w))

                selection_label_rects.append(text_rect)

        # --------------------------------------------------------------
        # Tick label'ları ile çakışma kontrol yardımcıları
        # --------------------------------------------------------------
        drawn_tick_label_rects = []  # normal tick label rect'leri

        def intersects_any(rect_list, candidate) -> bool:
            for r in rect_list:
                if r.intersects(candidate):
                    return True
            return False

        def build_label_rect(center_x: float, extra_margin: float = 4.0) -> "QRectF":
            """
            Tick label'ı için yaklaşık bir rect üretir.
            """
            approx_rect = rect.adjusted(0, 0, 0, -4)
            left = int(center_x - 20.0)
            right = int(center_x + 20.0)
            approx_rect.setLeft(left)
            approx_rect.setRight(right)
            return approx_rect

        def can_draw_tick_label(x_tick: float) -> bool:
            """
            Bu tick label'ı, hem diğer tick label'larıyla hem de seçim label'larıyla
            çakışmıyorsa True döndürür.
            """
            candidate = build_label_rect(x_tick)

            # 1) Seçim label'larının üstüne binme
            if intersects_any(selection_label_rects, candidate):
                return False

            # 2) Diğer tick label'ları ile çakışma
            if intersects_any(drawn_tick_label_rects, candidate):
                return False

            drawn_tick_label_rects.append(candidate)
            return True

        # --------------------------------------------------------------
        # 1. pozisyon (pozisyon 1 tick'i)
        # --------------------------------------------------------------
        if 1 >= first_pos and 1 <= last_pos:
            pos = 1
            center_scene_x = (pos - 0.5) * char_width
            x = center_scene_x - view_left
            if 0 <= x <= width:
                painter.setPen(normal_pen)
                painter.drawLine(int(x), baseline_y, int(x), baseline_y - tick_h)

                if can_draw_tick_label(x):
                    label_text = "1"
                    text_width = metrics.horizontalAdvance(label_text)
                    half_w = text_width / 2.0

                    text_rect = rect.adjusted(0, 0, 0, -4)
                    text_rect.setLeft(int(x - half_w))
                    text_rect.setRight(int(x + half_w))
                    painter.drawText(
                        text_rect, Qt.AlignHCenter | Qt.AlignTop, label_text
                    )

        # --------------------------------------------------------------
        # Ana tick'ler
        # --------------------------------------------------------------
        start_mult = max(step, first_pos)
        start_pos = ((start_mult + step - 1) // step) * step

        pos = start_pos
        while pos <= last_pos:
            center_scene_x = (pos - 0.5) * char_width
            x = center_scene_x - view_left
            if 0 <= x <= width:
                painter.setPen(normal_pen)
                painter.drawLine(int(x), baseline_y, int(x), baseline_y - tick_h)

                if can_draw_tick_label(x):
                    label = str(pos)
                    text_rect = rect.adjusted(0, 0, 0, -4)
                    half_w = metrics.horizontalAdvance(label) / 2.0
                    text_rect.setLeft(int(x - half_w))
                    text_rect.setRight(int(x + half_w))
                    painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, label)

            pos += step

        # --------------------------------------------------------------
        # Seçili pozisyonlar için özel (bold/blue) label'lar
        # --------------------------------------------------------------
        if special_positions:
            bold_font = QFont(self.font)
            bold_font.setBold(True)
            blue_pen = QPen(QColor(0, 0, 200))

            painter.setFont(bold_font)
            painter.setPen(blue_pen)

            drawn_special_rects = []

            def build_special_rect(center_x: float, label_text: str) -> "QRectF":
                tw = metrics.horizontalAdvance(label_text)
                half_w = tw / 2.0
                r = rect.adjusted(0, 0, 0, -4)
                r.setLeft(int(center_x - half_w))
                r.setRight(int(center_x + half_w))
                return r

            def can_draw_special(center_x: float, label_text: str) -> bool:
                candidate = build_special_rect(center_x, label_text)
                if intersects_any(drawn_special_rects, candidate):
                    return False
                drawn_special_rects.append(candidate)
                return True

            drawn_special = set()

            for pos in special_positions:
                if pos in drawn_special:
                    continue
                drawn_special.add(pos)
                if pos < first_pos or pos > last_pos:
                    continue

                center_scene_x = (pos - 0.5) * char_width
                x = center_scene_x - view_left
                if x < 0 or x > width:
                    continue

                label = str(pos)
                if not can_draw_special(x, label):
                    continue

                text_rect = rect.adjusted(0, 0, 0, -4)
                text_rect.setLeft(int(x - metrics.horizontalAdvance(label) / 2.0))
                text_rect.setRight(int(x + metrics.horizontalAdvance(label) / 2.0))
                painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, label)

        painter.end()
