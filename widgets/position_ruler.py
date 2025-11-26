# msa_viewer/widgets/position_ruler.py

import math
from typing import Optional

from PyQt5.QtCore import Qt, QRectF

# (rest of file as you sent, just import SequenceViewerWidget relatively)

from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics
from PyQt5.QtWidgets import QWidget, QScrollBar

from .sequence_viewer import SequenceViewerWidget


class SequencePositionRulerWidget(QWidget):
    """
    Sequence row'larının hemen üstünde duran ikinci ruler.

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

        hbar: QScrollBar = self.viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self._on_view_changed)
        hbar.rangeChanged.connect(self._on_view_changed)
        self.viewer.selectionChanged.connect(self._on_view_changed)

    def _on_view_changed(self, *_args) -> None:
        self.update()

    def _get_max_sequence_length(self) -> int:
        if not self.viewer.sequence_items:
            return 0
        return max(len(item.sequence) for item in self.viewer.sequence_items)

    def _choose_step_for_zoom(self, char_width: float, visible_span: int) -> int:
        """
        Görünen nt aralığına ve zoom seviyesine göre "güzel" tick/label aralığı seçer.
        Profesyonel araçlar (Geneious, IGV) bu mantıkla çalışır.
        """
        if visible_span <= 0:
            return 1

        # 1. Temel hedef: ekranda yaklaşık 8–12 ana label olsun
        target_labels = 10.0
        raw_step = visible_span / target_labels

        if raw_step <= 1:
            return 1

        # 2. Nice number (1, 2, 5 × 10^k)
        import math

        power = 10 ** int(math.floor(math.log10(raw_step)))
        base = raw_step / power

        if base <= 1.5:
            nice = 1
        elif base <= 3:
            nice = 2
        elif base <= 7:
            nice = 5
        else:
            nice = 10

        candidate = int(nice * power)

        # 3. Özel kurallar: çok büyük/küçük span'lerde daha seyrek/sık yap
        if visible_span >= 1_000_000:  # 1M+
            # Çok uzak zoom → 100K, 200K, 500K, 1M gibi
            candidate = self._round_to_nice_large(candidate)
        elif visible_span >= 100_000:  # 100K–1M
            candidate = max(candidate, 10_000)
        elif visible_span <= 100:  # Çok yakın zoom
            candidate = min(candidate, 10)

        return max(candidate, 1)

    def _round_to_nice_large(self, step: int) -> int:
        """1M+ görünürken daha güzel aralıklar: 100K, 200K, 500K, 1M, 2M, 5M..."""
        if step < 100_000:
            return 100_000
        elif step <= 200_000:
            return 200_000
        elif step <= 500_000:
            return 500_000
        elif step <= 1_000_000:
            return 1_000_000
        elif step <= 2_000_000:
            return 2_000_000
        elif step <= 5_000_000:
            return 5_000_000
        else:
            # 10M, 20M, 50M...
            power = 10 ** int(math.log10(step))
            base = step // power
            if base <= 2:
                return 2 * power
            elif base <= 5:
                return 5 * power
            else:
                return 10 * power

    def paintEvent(self, event) -> None:
        # (tamamen senin son gönderdiğin versiyon; sadece SequenceViewer import'u değişti)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        rect = self.rect()
        width = rect.width()
        height = rect.height()

        painter.fillRect(rect, QBrush(Qt.white))

        max_len = self._get_max_sequence_length()
        if max_len <= 0 or width <= 0:
            painter.setPen(QPen(Qt.black))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            painter.end()
            return

        painter.setPen(QPen(Qt.black))
        painter.drawLine(
            rect.left(), rect.bottom() - 1, rect.right(), rect.bottom() - 1
        )

        view_scene_rect = self.viewer.mapToScene(
            self.viewer.viewport().rect()
        ).boundingRect()

        view_left = float(view_scene_rect.left())
        view_width = float(view_scene_rect.width())

        # Zoom animasyonundaki anlık değeri yakalayabilmek için, varsa
        # viewer'ın _get_current_char_width helper'ını kullan.
        if hasattr(self.viewer, "_get_current_char_width"):
            char_width = float(self.viewer._get_current_char_width())  # type: ignore[attr-defined]
        else:
            char_width = float(self.viewer.char_width)

        if char_width <= 0 or view_width <= 0:
            painter.end()
            return

        painter.setFont(self.font)
        metrics = painter.fontMetrics()

        first_col = int(math.floor(view_left / char_width))
        last_col = int(math.ceil((view_left + view_width) / char_width))

        first_col = max(0, first_col)
        last_col = min(max_len, last_col)

        if last_col <= first_col:
            painter.end()
            return

        first_pos = first_col + 1
        last_pos = last_col

        visible_span = last_pos - first_pos + 1
        step = self._choose_step_for_zoom(char_width, visible_span)

        baseline_y = height - 2
        tick_h = 6

        normal_pen = QPen(QColor(0, 0, 0))
        painter.setPen(normal_pen)

        sel_cols = self.viewer.current_selection_cols
        sel_start_pos = sel_end_pos = None
        if sel_cols is not None:
            s, e = sel_cols
            if s > e:
                s, e = e, s
            sel_start_pos = s + 1
            sel_end_pos = e + 1

        # Seçili pozisyonlar (başlangıç / bitiş) piksel koordinatları ve text rect'leri
        special_positions = []
        if sel_start_pos is not None:
            special_positions.append(sel_start_pos)
            if sel_end_pos is not None and sel_end_pos != sel_start_pos:
                special_positions.append(sel_end_pos)
        # metrics'i bir kez üret (paintEvent'in üst tarafında olabilir)
        metrics = QFontMetrics(self.font)

        # Seçili pozisyonlar (başlangıç / bitiş) piksel koordinatları ve text rect'leri
        special_positions = []
        if sel_start_pos is not None:
            special_positions.append(sel_start_pos)
            if sel_end_pos is not None and sel_end_pos != sel_start_pos:
                special_positions.append(sel_end_pos)

        selected_xs = []  # sadece merkez x değerleri
        selection_label_rects = []  # seçim label'larının gerçek rect'leri

        for pos in special_positions:
            if pos < first_pos or pos > last_pos:
                continue

            center_scene_x = (pos - 0.5) * char_width
            x = center_scene_x - view_left
            if 0 <= x <= width:
                selected_xs.append(x)

                # Label text ve genişlik
                label_text = str(pos)
                text_width = metrics.horizontalAdvance(label_text)
                half_w = text_width / 2.0

                # Yatayda ortalanmış gerçek rect
                text_rect = rect.adjusted(0, 0, 0, -4)
                text_rect.setLeft(int(x - half_w))
                text_rect.setRight(int(x + half_w))

                selection_label_rects.append(text_rect)

        painter.setPen(normal_pen)
        painter.setFont(self.font)
        # Tick label'larının birbirleriyle ve seçim label'larıyla çakışmasını engelle
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

            # Çizebiliriz, artık bunu da listeye ekleyelim
            drawn_tick_label_rects.append(candidate)
            return True

        # 1. pozisyon
        if 1 >= first_pos and 1 <= last_pos:
            pos = 1
            center_scene_x = (pos - 0.5) * char_width
            x = center_scene_x - view_left
            if 0 <= x <= width:
                painter.setPen(normal_pen)
                painter.drawLine(int(x), baseline_y, int(x), baseline_y - tick_h)

                # NORMAL TICK LABEL ÇİZİMİ (düzeltildi)
                if can_draw_tick_label(x):
                    label_text = "1" if pos == 1 else str(pos)
                    text_width = metrics.horizontalAdvance(label_text)
                    half_w = text_width / 2.0

                    text_rect = rect.adjusted(0, 0, 0, -4)
                    text_rect.setLeft(int(x - half_w))
                    text_rect.setRight(int(x + half_w))
                    painter.drawText(
                        text_rect, Qt.AlignHCenter | Qt.AlignTop, label_text
                    )
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
