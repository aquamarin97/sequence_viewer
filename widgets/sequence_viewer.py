# msa_viewer/widgets/sequence_viewer.py

from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QPointF, QEasingCurve, QVariantAnimation, pyqtSignal
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QScrollBar
from math import pow  # eğer dosyanın başında yoksa
from graphics.sequence_item import SequenceGraphicsItem


class SequenceViewerWidget(QGraphicsView):
    """
    Sadece sekansları çizen viewer.
    Solda header alanı yok; o, ayrı bir HeaderViewerWidget içinde.
    """

    # Seçim değiştiğinde ruler'ı güncellemek için sinyal
    selectionChanged = pyqtSignal()

    def __init__(
        self,
        parent=None,
        char_width: float = 12.0,
        char_height: float = 18.0,
    ) -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.max_sequence_length: int = 0  # 🔹 Ruler için cache
        self.trailing_padding_line_px: float = 80.0
        self.trailing_padding_text_px: float = 30.0
        self.char_width = char_width
        self.char_height = int(round(char_height))

        self._zoom_animation = QVariantAnimation(self)
        self._zoom_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._zoom_animation.valueChanged.connect(self._on_zoom_value_changed)

        self._zoom_center_nt: Optional[float] = None
        self._zoom_view_width_px: Optional[float] = None

        # Ctrl + wheel “streak” hızlandırma için:
        self._wheel_zoom_streak_dir: Optional[int] = None
        self._wheel_zoom_streak_len: int = 0
        self._wheel_zoom_base_factor = 1.22
        self._wheel_zoom_accel_factor = 1.06

        self.sequence_items: List[SequenceGraphicsItem] = []

        # Seçim durumu
        self.is_selecting = False
        self.selection_start_row: Optional[int] = None
        self.selection_start_col: Optional[int] = None

        # Şu anki seçim sütun aralığı (start, end) inclusive
        self.current_selection_cols: Optional[Tuple[int, int]] = None

        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)

    # --------- Public API ---------

    def add_sequence(self, sequence_string: str) -> None:
        row_index = len(self.sequence_items)
        item = SequenceGraphicsItem(
            sequence=sequence_string,
            char_width=self.char_width,
            char_height=self.char_height,
        )
        item.setPos(0, row_index * self.char_height)
        self.scene.addItem(item)
        self.sequence_items.append(item)
        self._update_scene_rect()

    def clear(self) -> None:
        self.sequence_items.clear()
        self.scene.clear()
        self._update_scene_rect()

    # --------- Scene boyutu ---------

    def _update_scene_rect(self) -> None:
        if not self.sequence_items:
            self.scene.setSceneRect(0, 0, 0, 0)
            self.max_sequence_length = 0  # 🔹 boşken 0
            return

        max_len = max(len(item.sequence) for item in self.sequence_items)
        self.max_sequence_length = max_len  # 🔹 cache burada güncelleniyor
        trailing_padding = self._current_trailing_padding()

        width = max_len * self.char_width + trailing_padding
        height = len(self.sequence_items) * self.char_height
        self.scene.setSceneRect(0, 0, width, height)
        self.scene.invalidate()

    def _current_trailing_padding(self) -> float:
        if not self.sequence_items:
            return self.trailing_padding_text_px

        # Tüm satırlar aynı char_width'e sahip olduğu için tekini kontrol etmek yeterli.
        first_item_mode = self.sequence_items[0].display_mode
        if first_item_mode == SequenceGraphicsItem.LINE_MODE:
            return self.trailing_padding_line_px

        # TEXT ve BOX modunda daha küçük padding.
        return self.trailing_padding_text_px

    # --------- Zoom yardımcıları ---------

    def _compute_min_char_width(self) -> float:
        if not self.sequence_items:
            return self.char_width

        max_len = self.max_sequence_length
        if max_len <= 0:
            return self.char_width

        viewport_width = self.viewport().width()
        if viewport_width <= 0:
            return self.char_width
        # LINE modunda padding daha geniş; zoom-out sırasında mod değişirse
        # sahne genişliği hesaplaması beklenenden büyük çıkıp scroll bar
        # görünmesin diye en geniş padding'i baz al.
        trailing_padding = max(
            self.trailing_padding_line_px, self._current_trailing_padding()
        )

        # Spacer'ı nt yerine sabit piksel olarak ekle
        available_width = viewport_width - trailing_padding
        if available_width <= 0:
            return 0.000001

        min_char_width = available_width / float(max_len)
        return max(min_char_width, 0.000001)

    def _effective_char_width(self) -> float:
        """Anlık geometriyi en iyi temsil eden karakter genişliği."""
        # 1) Animasyon akıyorsa ara değeri kullan (ruler + hit-test senkronu)
        if self._zoom_animation.state() == QVariantAnimation.Running:
            current_value = self._zoom_animation.currentValue()
            if current_value is not None:
                return float(current_value)

        # 2) Item'lar varsa, gerçekten uygulanan değeri kullan (clamp sonrası)
        if self.sequence_items:
            return float(self.sequence_items[0].char_width)

        # 3) Fallback: viewer'daki cache
        return float(self.char_width)

    # Backward compatible helper (position ruler vs. hit-test)
    def _get_current_char_width(self) -> float:
        return self._effective_char_width()

    def _recenter_horizontally(self, center_nt: float, view_width_px: float) -> None:
        """
        centerOn yerine yalnızca horizontalScrollBar ile yeniden merkezleme.
        Böylece:
        - vbar'a hiç dokunmuyoruz,
        - int yuvarlama kaynaklı 1px jitter'ı minimize ediyoruz.
        """
        if view_width_px <= 0:
            view_width_px = float(self.viewport().width())
            if view_width_px <= 0:
                return

        scene_width = float(self.scene.sceneRect().width())
        if scene_width <= 0:
            return

        # nt aralığına clamp
        if self.max_sequence_length > 0:
            center_nt = max(0.0, min(center_nt, float(self.max_sequence_length)))

        cw = self._effective_char_width()
        center_x = center_nt * cw
        ideal_left = center_x - view_width_px / 2.0

        # Scene genişliğine göre clamp
        max_left = max(0.0, scene_width - view_width_px)
        ideal_left = max(0.0, min(ideal_left, max_left))

        hbar: QScrollBar = self.horizontalScrollBar()
        current_left = float(hbar.value())

        # Çok küçük farklar için setValue çağırma → 1px ileri-geri titremeyi azaltır
        if abs(ideal_left - current_left) < 0.5:
            return

        hbar.setValue(int(round(ideal_left)))

    def _apply_char_width(
        self,
        new_char_width: float,
        center_nt: Optional[float],
        view_width_px: float,
    ) -> None:
        # char_width gerçekten değişmiyorsa ve pivot yoksa uğraşma
        if abs(new_char_width - self.char_width) < 0.0001 and center_nt is None:
            return

        # 1) Yeni char_width'ü uygula
        applied_width = float(new_char_width)
        for item in self.sequence_items:
            item.set_char_width(applied_width)

        # Item clamp/prepareGeometryChange'inden sonra gerçek değeri sakla
        if self.sequence_items:
            applied_width = float(self.sequence_items[0].char_width)
        self.char_width = applied_width
        self._update_scene_rect()

        # 2) Pivot nt etrafında yatayda yeniden merkezle
        if center_nt is not None:
            self._recenter_horizontally(center_nt, view_width_px)

        # LOD güncelle (varsa)
        if hasattr(self, "_update_lod_for_all_items"):
            self._update_lod_for_all_items()

        self.viewport().update()

    def _start_zoom_animation(
        self,
        target_char_width: float,
        center_nt: float,
        view_width_px: float,
    ) -> None:
        current_char_width = self._get_current_char_width()

        # Hedefle mevcut aynıysa direkt uygula
        if abs(target_char_width - current_char_width) < 0.0001:
            self._apply_char_width(target_char_width, center_nt, view_width_px)
            return

        # Animasyon zaten çalışıyorsa:
        # - pivotu sabit tut (ilk başlatıldığında ne ise o),
        # - sadece yeni hedef genişliği güncelle.
        if self._zoom_animation.state() == QVariantAnimation.Running:
            # viewport genişliği değişmiş olabilir, güncelle
            self._zoom_view_width_px = view_width_px
            # center_nt'i BİLEREK değiştirmiyoruz → drift yok
            self._zoom_animation.setEndValue(target_char_width)
            return

        # Animasyon çalışmıyorsa, yeni bir tane başlat
        self._zoom_center_nt = center_nt
        self._zoom_view_width_px = view_width_px

        self._zoom_animation.setDuration(180)  # istersen 140–200 ms oynayabilirsin
        self._zoom_animation.setStartValue(current_char_width)
        self._zoom_animation.setEndValue(target_char_width)
        self._zoom_animation.start()

    def _on_zoom_value_changed(self, value) -> None:
        if self._zoom_center_nt is None or self._zoom_view_width_px is None:
            return

        try:
            new_char_width = float(value)
        except (TypeError, ValueError):
            return

        self._apply_char_width(
            new_char_width,
            self._zoom_center_nt,
            float(self._zoom_view_width_px),
        )

    def wheelEvent(self, event) -> None:
        # Ctrl yoksa → normal scroll
        if not (event.modifiers() & Qt.ControlModifier):
            super().wheelEvent(event)
            return

        delta = event.angleDelta().y()
        if delta == 0 or not self.sequence_items:
            return

        # ---------------- Zoom streak takibi (hızlandırma) ----------------
        steps = delta / 120.0
        direction = 1 if steps > 0 else -1
        if self._wheel_zoom_streak_dir == direction:
            self._wheel_zoom_streak_len += 1
        else:
            self._wheel_zoom_streak_dir = direction
            self._wheel_zoom_streak_len = 1

        hbar: QScrollBar = self.horizontalScrollBar()
        view_width_px = float(self.viewport().width())
        if view_width_px <= 0:
            return

        current_cw = self._get_current_char_width()
        if current_cw <= 0:
            current_cw = max(self.char_width, 0.001)

        # ---------------- Pivot nt hesaplama ----------------
        if (
            self._zoom_animation.state() == QVariantAnimation.Running
            and self._zoom_center_nt is not None
        ):
            # Zoom animasyonu zaten akıyorsa → aynı pivotu kullan
            center_nt = self._zoom_center_nt
        elif self.current_selection_cols is not None and self.max_sequence_length > 0:
            # Seçim varsa, onun ortasını pivot al
            s, e = self.current_selection_cols
            if s > e:
                s, e = e, s
            center_nt = (s + e + 1) / 2.0
            center_nt = max(0.0, min(center_nt, float(self.max_sequence_length)))
        else:
            # Aksi halde: mouse'un altındaki nt’yi pivot al
            old_left_px = float(hbar.value())
            cursor_x = float(event.pos().x())
            scene_x = old_left_px + cursor_x
            center_nt = scene_x / current_cw
        # ---------------- Zoom faktörü (streak ile hızlanma) ----------------
        streak_boost = pow(
            self._wheel_zoom_accel_factor,
            max(0, self._wheel_zoom_streak_len - 1),
        )
        self._wheel_zoom_streak_len

        per_step_factor = self._wheel_zoom_base_factor * streak_boost
        magnitude_factor = pow(per_step_factor, abs(steps))
        factor = magnitude_factor if direction > 0 else 1.0 / magnitude_factor

        target_cw = current_cw * factor

        # ---------------- Min/Max clamp ----------------
        min_char_width = self._compute_min_char_width()
        max_char_width = 90.0
        target_cw = max(min_char_width, min(target_cw, max_char_width))

        if abs(target_cw - current_cw) < 0.0001:
            return

        # ---------------- Animasyonu başlat ----------------
        self._start_zoom_animation(
            target_char_width=target_cw,
            center_nt=center_nt,
            view_width_px=view_width_px,
        )

    # --------- Seçim ---------

    def _clamp_column_index(self, col: int) -> Optional[int]:
        if self.max_sequence_length <= 0:
            return None
        return max(0, min(col, self.max_sequence_length - 1))

    def _scene_pos_to_row_col(self, scene_pos: QPointF) -> Tuple[int, int]:
        row = int(scene_pos.y() // self.char_height)
        # Zoom animasyonu sırasında ruler ve hit-test arasında kayma olmaması için
        # anlık karakter genişliğini (animasyon değerini) kullan.
        current_cw = getattr(self, "_get_current_char_width", None)
        if callable(current_cw):
            cw = float(current_cw())
        else:
            cw = float(self.char_width)

        if cw <= 0:
            cw = float(self.char_width) if self.char_width > 0 else 0.000001

        col = int(scene_pos.x() // cw)
        return row, col

    def _clear_all_selections(self) -> None:
        for item in self.sequence_items:
            item.clear_selection()
        self.current_selection_cols = None
        self.selection_start_row = None
        self.selection_start_col = None
        self.selectionChanged.emit()

    def _update_selection(self, current_row: int, current_col: int) -> None:
        if self.selection_start_row is None or self.selection_start_col is None:
            return

        clamped_start_col = self._clamp_column_index(self.selection_start_col)
        clamped_current_col = self._clamp_column_index(current_col)
        if clamped_start_col is None or clamped_current_col is None:
            self._clear_all_selections()
            return

        row_start = max(0, min(self.selection_start_row, current_row))
        row_end = min(
            len(self.sequence_items) - 1, max(self.selection_start_row, current_row)
        )

        col_start = min(clamped_start_col, clamped_current_col)
        col_end = max(clamped_start_col, clamped_current_col)

        # Sadece sütun aralığını kaydediyoruz (ruler satırdan bağımsız)
        if col_start >= 0 and col_end >= 0:
            self.current_selection_cols = (col_start, col_end)
        else:
            self.current_selection_cols = None

        for row_index, item in enumerate(self.sequence_items):
            if row_start <= row_index <= row_end and col_start >= 0 and col_end >= 0:
                item.set_selection(col_start, col_end)
            else:
                item.clear_selection()

        self.selectionChanged.emit()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            row, col = self._scene_pos_to_row_col(scene_pos)
            if 0 <= row < len(self.sequence_items) and col >= 0:
                self.is_selecting = True
                self.selection_start_row = row
                self.selection_start_col = col
                self._update_selection(row, col)
            else:
                self._clear_all_selections()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.is_selecting and self.selection_start_row is not None:
            scene_pos = self.mapToScene(event.pos())
            row, col = self._scene_pos_to_row_col(scene_pos)
            self._update_selection(row, col)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
        else:
            super().mouseReleaseEvent(event)

    # Cetvelden aralığa zoom:

    def zoom_to_nt_range(self, start_nt: float, end_nt: float) -> None:
        if not self.sequence_items:
            return

        a = float(start_nt)
        b = float(end_nt)
        if a == b:
            span_nt = 1.0
            center_nt = a
        else:
            left_nt = min(a, b)
            right_nt = max(a, b)
            span_nt = max(right_nt - left_nt, 1.0)
            center_nt = (left_nt + right_nt) / 2.0

        viewport_width_px = float(self.viewport().width())
        if viewport_width_px <= 0:
            return

        desired_char_width = viewport_width_px / span_nt

        min_char_width = self._compute_min_char_width()
        max_char_width = 90.0
        new_char_width = max(min_char_width, min(desired_char_width, max_char_width))

        if abs(new_char_width - self.char_width) > 0.0001:
            self.char_width = new_char_width
            for item in self.sequence_items:
                item.set_char_width(self.char_width)
            self._update_scene_rect()

        # 🔹 Aynı yeniden merkezleme mantığını burada da kullan
        self._recenter_horizontally(center_nt, viewport_width_px)
        self.viewport().update()
