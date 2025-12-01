# msa_viewer/sequence_viewer/sequence_viewer_controller.py

from typing import Optional, Callable

from math import pow

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QScrollBar

from .sequence_viewer_model import SequenceViewerModel
from .sequence_viewer_view import SequenceViewerView


class SequenceViewerController:
    """
    SequenceViewer'ın CMV mimarisindeki Controller katmanı.

    Sorumluluklar:
    - Model <-> View köprüsü
    - Zoom + wheel davranışı
    - Mouse ile seçim (press / move / release) mantığı
    - Model seçim state'ini güncellemek ve View'e highlight'ları uygulatmak
    """

    def __init__(
        self,
        model: SequenceViewerModel,
        view: SequenceViewerView,
        *,
        on_selection_changed: Optional[Callable[[], None]] = None,
    ) -> None:
        self._model = model
        self._view = view

        # Seçim drag state'i
        self._is_selecting: bool = False

        # Ctrl + wheel “streak” hızlandırma state'i
        self._wheel_zoom_streak_dir: Optional[int] = None
        self._wheel_zoom_streak_len: int = 0
        self._wheel_zoom_base_factor: float = 1.22
        self._wheel_zoom_accel_factor: float = 1.06

        # Widget'tan gelen seçim değişimi callback'i (PyQt sinyali bağlanıyor)
        self._on_selection_changed = on_selection_changed

    # ------------------------------------------------------------------
    # Model <-> View ekleme / temizleme
    # ------------------------------------------------------------------

    def add_sequence(self, sequence_string: str) -> None:
        """
        Yeni bir sekansı hem modele hem view'e ekler.
        """
        # Model'e ekle
        self._model.add_sequence(sequence_string)
        # View'da karşılık gelen item'ı oluştur
        self._view.add_sequence_item(sequence_string)

    def clear(self) -> None:
        """
        Tüm sekansları ve seçimleri temizler.
        """
        self._model.clear_sequences()
        self._view.clear_items()

        self._is_selecting = False
        self._wheel_zoom_streak_dir = None
        self._wheel_zoom_streak_len = 0

        self._notify_selection_changed()

    # ------------------------------------------------------------------
    # Seçim yönetimi (mouse event'lerinden çağrılır)
    # ------------------------------------------------------------------

    def handle_mouse_press(self, event) -> bool:
        """
        View.mousePressEvent'ten çağrılır.
        True dönerse event tamamen burada işlendi, View süpere göndermesin.
        """
        if event.button() != Qt.LeftButton:
            return False  # diğer butonlar için default davranış kalsın

        row_count = self._model.get_row_count()
        if row_count == 0:
            # Sekans yoksa seçim olmaz
            self._model.clear_selection()
            self._view.clear_visual_selection()
            self._notify_selection_changed()
            return True

        scene_pos = self._view.mapToScene(event.pos())
        row, col = self._view.scene_pos_to_row_col(scene_pos)

        if 0 <= row < row_count and col >= 0:
            # Geçerli bir seçim başlangıcı
            started = self._model.start_selection(row, col)
            if started:
                self._is_selecting = True
                sel_range = self._model.update_selection(row, col)
                if sel_range is not None:
                    row_start, row_end, col_start, col_end = sel_range
                    self._view.set_visual_selection(
                        row_start, row_end, col_start, col_end
                    )
                else:
                    self._view.clear_visual_selection()
                self._notify_selection_changed()
        else:
            # Boşa tıklandı → seçimi temizle
            self._model.clear_selection()
            self._view.clear_visual_selection()
            self._is_selecting = False
            self._notify_selection_changed()

        return True

    def handle_mouse_move(self, event) -> bool:
        """
        Drag sırasında çağrılır.
        """
        if not self._is_selecting or self._model.selection_start_row is None:
            return False

        scene_pos = self._view.mapToScene(event.pos())
        row, col = self._view.scene_pos_to_row_col(scene_pos)

        sel_range = self._model.update_selection(row, col)
        if sel_range is not None:
            row_start, row_end, col_start, col_end = sel_range
            self._view.set_visual_selection(
                row_start, row_end, col_start, col_end
            )
        else:
            self._view.clear_visual_selection()

        self._notify_selection_changed()
        return True

    def handle_mouse_release(self, event) -> bool:
        """
        Mouse bırakıldığında çağrılır.
        """
        if event.button() == Qt.LeftButton and self._is_selecting:
            self._is_selecting = False
            # Seçim zaten update_selection içinde finalize oldu.
            return True

        return False

    # ------------------------------------------------------------------
    # Zoom / WheelEvent
    # ------------------------------------------------------------------

    def handle_wheel_event(self, event) -> bool:
        """
        Ctrl + wheel zoom mantığını yönetir.
        True dönerse event burada işlenmiştir (view.super().wheelEvent çağrılmamalı).
        """
        # Ctrl yoksa → normal scroll
        if not (event.modifiers() & Qt.ControlModifier):
            return False

        # Ctrl basılıysa zoom modundayız, default scroll'u engelliyoruz
        delta = event.angleDelta().y()
        if delta == 0 or not self._view.sequence_items:
            return True  # event işlendi, ama zoom yok

        # ---------------- Zoom streak takibi (hızlandırma) ----------------
        steps = delta / 120.0
        direction = 1 if steps > 0 else -1

        if self._wheel_zoom_streak_dir == direction:
            self._wheel_zoom_streak_len += 1
        else:
            self._wheel_zoom_streak_dir = direction
            self._wheel_zoom_streak_len = 1

        hbar: QScrollBar = self._view.horizontalScrollBar()
        view_width_px = float(self._view.viewport().width())
        if view_width_px <= 0:
            return True

        current_cw = self._view.current_char_width()
        if current_cw <= 0:
            current_cw = max(self._view.char_width, 0.001)

        # ---------------- Pivot nt hesaplama ----------------
        # Önce seçim ortasını pivot almaya çalış
        center_nt = self._model.get_selection_center_nt()
        if center_nt is None:
            # Seçim yoksa: mouse altındaki nt'yi pivot al
            old_left_px = float(hbar.value())
            cursor_x = float(event.pos().x())
            scene_x = old_left_px + cursor_x
            center_nt = scene_x / current_cw

        # ---------------- Zoom faktörü (streak ile hızlanma) ----------------
        streak_boost = pow(
            self._wheel_zoom_accel_factor,
            max(0, self._wheel_zoom_streak_len - 1),
        )

        per_step_factor = self._wheel_zoom_base_factor * streak_boost
        magnitude_factor = pow(per_step_factor, abs(steps))
        factor = magnitude_factor if direction > 0 else 1.0 / magnitude_factor

        target_cw = current_cw * factor

        # ---------------- Min/Max clamp ----------------
        min_char_width = self._view.compute_min_char_width()
        max_char_width = 90.0
        target_cw = max(min_char_width, min(target_cw, max_char_width))

        if abs(target_cw - current_cw) < 0.0001:
            return True  # değişmeyecek, ama event bize ait

        # ---------------- Animasyonu başlat ----------------
        self._view.start_zoom_animation(
            target_char_width=target_cw,
            center_nt=center_nt,
            view_width_px=view_width_px,
        )

        return True

    # ------------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------------

    def _notify_selection_changed(self) -> None:
        """
        Widget'tan bağlanan seçim değişimi callback'ini tetikler (PyQt sinyali).
        """
        if self._on_selection_changed is not None:
            self._on_selection_changed()
