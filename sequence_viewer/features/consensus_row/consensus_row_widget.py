# sequence_viewer/features/consensus_row/consensus_row_widget.py
"""
Consensus satırı widget'ı.
Mouse handling → ConsensusMouseController
Drag state     → ConsensusDragController
Annotation sel → ConsensusAnnotationHandler
Rendering      → ConsensusRenderer
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

from PyQt5.QtCore import Qt, pyqtSignal, QRectF
from PyQt5.QtGui import QFont, QPainter
from PyQt5.QtWidgets import QWidget

from sequence_viewer.features.annotation_layer.annotation_layout_engine import (
    partition_annotations_by_side,
    side_strip_height,
)
from sequence_viewer.features.consensus_row.consensus_annotation_handler import (
    ConsensusAnnotationHandler,
)
from sequence_viewer.features.consensus_row.consensus_drag_controller import ConsensusDragController
from sequence_viewer.features.consensus_row.consensus_mouse_controller import ConsensusMouseController
from sequence_viewer.features.consensus_row.consensus_renderer import ConsensusRenderer
from sequence_viewer.features.consensus_row.consensus_row_model import ConsensusRowModel
from sequence_viewer.model.consensus_calculator import ConsensusMethod
from sequence_viewer.settings.display_settings_manager import display_settings_manager
from sequence_viewer.settings.theme import theme_manager
from sequence_viewer.utils.drag_tooltip import DragTooltip
from sequence_viewer.utils.sequence_utils import calculate_tm, selection_bp


class ConsensusRowWidget(QWidget):
    # ── Sinyaller ─────────────────────────────────────────────────────────
    headerClearRequested = pyqtSignal()
    annotationEditRequested = pyqtSignal(object)
    workspaceAnnotationClearRequested = pyqtSignal()
    spacerSelectionChanged = pyqtSignal(bool)
    coordinatorRefreshRequested = pyqtSignal()
    copySequenceRequested = pyqtSignal()
    copyFastaRequested = pyqtSignal()
    deleteAnnotationsRequested = pyqtSignal(object)
    spacerSyncRequested = pyqtSignal(int, bool, float, float)
    positionRulerRefreshRequested = pyqtSignal()

    def __init__(self, alignment_model, sequence_viewer, parent=None):
        super().__init__(parent)
        self._alignment_model = alignment_model
        self._sequence_viewer = sequence_viewer

        # ── Model ve render ──────────────────────────────────────────────
        self._model = ConsensusRowModel(method=ConsensusMethod.PLURALITY)
        self._font = QFont(display_settings_manager.consensus_font_family)
        self._font.setStyleHint(QFont.Monospace)
        self._font.setFixedPitch(True)
        from sequence_viewer.settings.color_styles import color_style_manager as _csm
        self._color_map = _csm.consensus_nucleotide_color_map()
        self._renderer = ConsensusRenderer()
        self._hit_rects: list = []

        # ── Seçim state ──────────────────────────────────────────────────
        self._is_selected: bool = False
        self._selected_ann_ids: set = set()
        self._selection_ranges: list = []  # [(start_incl, end_excl), ...]

        # ── Alt controller'lar ───────────────────────────────────────────
        _tooltip = DragTooltip()
        self._ann_handler = ConsensusAnnotationHandler(alignment_model)
        self._drag_ctrl = ConsensusDragController(_tooltip)
        self._mouse_ctrl = ConsensusMouseController(
            self, sequence_viewer, self._ann_handler, self._drag_ctrl
        )
        self._drag_tooltip = _tooltip  # _update_drag_tooltip için referans

        # ── Qt widget ayarları ───────────────────────────────────────────
        ch = int(round(sequence_viewer.char_height))
        self.setFixedHeight(ch)
        self.setMinimumWidth(0)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setCursor(Qt.IBeamCursor)

        # ── Model sinyal bağlantıları ────────────────────────────────────
        self._alignment_model.rowAppended.connect(self._on_data_changed)
        self._alignment_model.rowRemoved.connect(self._on_data_changed)
        self._alignment_model.rowMoved.connect(self._on_data_changed)
        self._alignment_model.modelReset.connect(self._on_data_changed)
        for sig in (
            self._alignment_model.globalAnnotationAdded,
            self._alignment_model.globalAnnotationRemoved,
            self._alignment_model.globalAnnotationUpdated,
            self._alignment_model.consensusAnnotationAdded,
            self._alignment_model.consensusAnnotationRemoved,
            self._alignment_model.consensusAnnotationUpdated,
        ):
            sig.connect(lambda _: self._update_visibility())
        self._alignment_model.alignmentStateChanged.connect(self._on_alignment_changed)

        # ── Viewer sinyal bağlantıları ───────────────────────────────────
        hbar = self._sequence_viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self.update)
        hbar.rangeChanged.connect(self.update)
        anim = getattr(self._sequence_viewer, "_zoom_animation", None)
        if anim:
            anim.valueChanged.connect(self.update)
        if hasattr(sequence_viewer, "add_v_guide_observer"):
            sequence_viewer.add_v_guide_observer(self.update)

        # ── Tema / ayar sinyal bağlantıları ─────────────────────────────
        theme_manager.themeChanged.connect(lambda _: self._on_theme_changed())
        display_settings_manager.displaySettingsChanged.connect(self._on_display_settings_changed)
        try:
            from sequence_viewer.settings.color_styles import color_style_manager as _csm2
            _csm2.stylesChanged.connect(self._on_color_styles_changed)
        except Exception:
            pass
        try:
            from sequence_viewer.settings.annotation_styles import annotation_style_manager as _asm2
            _asm2.stylesChanged.connect(self._update_visibility)
        except Exception:
            pass

        self._update_visibility()

    # ── _selection property (drag + annotation seçimi için backing store) ─

    @property
    def _selection(self) -> Optional[Tuple[int, int]]:
        """İlk aralığı (start_incl, end_incl) olarak döndürür; yoksa None."""
        if self._selection_ranges:
            s, e = self._selection_ranges[0]
            return (s, e - 1)
        return None

    @_selection.setter
    def _selection(self, value: Optional[Tuple[int, int]]) -> None:
        if value is None:
            self._selection_ranges = []
        else:
            s, e = value  # end inclusive
            self._selection_ranges = [(s, e + 1)]

    # ── Model / konsensüs metotları ───────────────────────────────────────

    def set_method(self, method, threshold=None):
        self._model.set_method(method, threshold)
        self.update()

    @property
    def current_method(self):
        return self._model.method

    @property
    def current_threshold(self):
        return self._model.threshold

    def _get_consensus(self):
        sequences = [seq for _, seq in self._alignment_model.all_rows()]
        if not sequences:
            return None
        return self._model.get_consensus(sequences)

    # ── Seçim public API ─────────────────────────────────────────────────

    def has_selected_annotations(self) -> bool:
        return bool(self._selected_ann_ids)

    def get_selected_annotation_ids(self) -> set:
        return set(self._selected_ann_ids)

    def clear_selection(self):
        self._selection_ranges = []
        self._is_selected = False
        self._selected_ann_ids.clear()
        self._notify_spacer_selected(False)
        self.update()

    def set_selected(self, selected: bool):
        if self._is_selected == selected:
            return
        self._is_selected = selected
        self.update()

    def select_all(self):
        """Tüm konsensüs dizisini seçili hale getirir."""
        consensus = self._get_consensus()
        if consensus:
            self._selection_ranges = [(0, len(consensus))]
            self._is_selected = True
            self.update()

    def delete_selected_annotations(self):
        ann_ids = set(self._selected_ann_ids)
        if not ann_ids:
            return
        self.deleteAnnotationsRequested.emit(ann_ids)

    # ── Pano ─────────────────────────────────────────────────────────────

    def clipboard_sequence_text(self) -> str:
        consensus = self._get_consensus()
        if not consensus:
            return ""
        if self._selection is not None:
            col_start, col_end = self._selection
            return consensus[col_start:col_end + 1]
        return consensus

    def clipboard_fasta_text(self, label: str = "Consensus") -> str:
        consensus = self._get_consensus()
        if not consensus:
            return ""
        if self._selection is not None:
            col_start, col_end = self._selection
            seq = consensus[col_start:col_end + 1]
        else:
            seq = consensus
        return f">{label}\n{seq}"

    # ── Görünürlük ve yükseklik ───────────────────────────────────────────

    def _compute_heights(self):
        ch = int(round(self._sequence_viewer.char_height))
        annotations = (
            list(self._alignment_model.consensus_annotations)
            if self._alignment_model.is_aligned
            else []
        )
        above_anns, below_anns = partition_annotations_by_side(annotations)
        return side_strip_height(above_anns), ch, side_strip_height(below_anns)

    def _update_visibility(self):
        if self._alignment_model.is_aligned:
            above_h, ch, below_h = self._compute_heights()
            total = above_h + ch + below_h
            self.setFixedHeight(total)
            self.setVisible(True)
            self._sync_spacer(above_h, ch)
        else:
            self.setFixedHeight(0)
            self.setVisible(False)
            self._sync_spacer(0.0, float(int(round(self._sequence_viewer.char_height))))
        self.update()

    def _sync_spacer(self, above_h: float, char_h: float):
        self.spacerSyncRequested.emit(self.height(), self.height() > 0, float(above_h), float(char_h))

    def _on_alignment_changed(self, is_aligned):
        self._update_visibility()
        if is_aligned:
            self._model.invalidate()
            self.update()

    # ── Settings / tema callback'leri ────────────────────────────────────

    def _on_color_styles_changed(self):
        from sequence_viewer.settings.color_styles import color_style_manager as _csm
        self._color_map = _csm.consensus_nucleotide_color_map()
        self._model.invalidate()
        self.update()

    def _on_data_changed(self, *_):
        self._model.invalidate()
        self.update()

    def _on_theme_changed(self):
        self._on_color_styles_changed()

    def _on_display_settings_changed(self):
        self._font.setFamily(display_settings_manager.consensus_font_family)
        self._update_visibility()
        self.update()

    # ── Koordinat yardımcıları ────────────────────────────────────────────

    def _get_char_width(self) -> float:
        return float(self._sequence_viewer.current_char_width())

    def _get_view_left(self) -> float:
        return float(self._sequence_viewer.horizontalScrollBar().value())

    def _col_at_x(self, x):
        cw = self._get_char_width()
        if cw <= 0:
            return None
        col = int((x + self._get_view_left()) / cw)
        consensus = self._get_consensus()
        if consensus is None:
            return None
        return max(0, min(col, len(consensus) - 1))

    def _scene_col_at_x(self, vp_x: float) -> int:
        cw = self._get_char_width()
        if cw <= 0:
            return 0
        return int((vp_x + self._get_view_left()) / cw)

    def _boundary_col_at_x(self, vp_x: float) -> int:
        cw = self._get_char_width()
        if cw <= 0:
            return 0
        return int(round((vp_x + self._get_view_left()) / cw))

    def _sync_font_from_viewer(self):
        items = getattr(self._sequence_viewer, "sequence_items", None)
        if items:
            size = float(items[0]._model.current_font_size) + 1.0
        else:
            cw = self._get_char_width()
            cw_default = float(getattr(self._sequence_viewer, "char_width", 12.0)) or 12.0
            scale = cw / cw_default
            con_base = display_settings_manager.consensus_font_size_base
            if scale >= 1.8:
                size = con_base
            elif scale >= 1.2:
                size = max(1.0, con_base * (10.0 / 12.0))
            elif scale >= 0.7:
                size = max(1.0, con_base * (8.0 / 12.0))
            else:
                size = max(1.0, display_settings_manager.consensus_char_height * 0.6 * scale)
        self._font.setPointSizeF(max(1.0, size))

    def _effective_mode(self):
        items = getattr(self._sequence_viewer, "sequence_items", None)
        if items:
            return items[0]._model.get_effective_mode()
        return "text"

    # ── Guide yönetimi ────────────────────────────────────────────────────

    def _get_controller(self):
        return getattr(self._sequence_viewer, "_controller", None)

    def _guide_cols(self) -> list:
        ctrl = self._get_controller()
        if ctrl is None:
            return []
        return list(getattr(ctrl, "v_guide_cols", []))

    def _set_guide_cols(self, cols: list) -> None:
        ctrl = self._get_controller()
        if ctrl is not None and hasattr(ctrl, "set_v_guides"):
            ctrl.set_v_guides(cols)
        else:
            self._sequence_viewer.set_v_guides(cols)

    def _clear_guide_cols(self) -> None:
        ctrl = self._get_controller()
        if ctrl is not None and hasattr(ctrl, "clear_v_guides"):
            ctrl.clear_v_guides()
        else:
            self._sequence_viewer.clear_v_guides()

    # ── Annotation hit testi ──────────────────────────────────────────────

    def _annotation_at(self, pos):
        p = QRectF(pos.x(), pos.y(), 1, 1)
        for rect, ann in self._hit_rects:
            if rect.intersects(p):
                return ann
        return None

    # ── Bildirim metodları (sinyal wrap'leri) ─────────────────────────────

    def _notify_spacer_selected(self, selected: bool) -> None:
        self.spacerSelectionChanged.emit(selected)

    def _notify_workspace_ann_cleared(self) -> None:
        self.workspaceAnnotationClearRequested.emit()

    def _notify_coordinator_refresh(self) -> None:
        self.coordinatorRefreshRequested.emit()

    # ── Drag tooltip ──────────────────────────────────────────────────────

    def _update_drag_tooltip(self, event) -> None:
        sel = self._selection
        if sel is None:
            self._drag_tooltip.clear_tooltip()
            return
        lo, hi = sel
        if hi <= lo:
            self._drag_tooltip.clear_tooltip()
            return
        bp = selection_bp(lo, hi)
        consensus = self._get_consensus()
        tm = calculate_tm(consensus[lo:hi + 1]) if consensus else None
        self._drag_tooltip.show_bp_tm(self.mapToGlobal(event.pos()), bp, tm)

    # ── Qt olayları ───────────────────────────────────────────────────────

    def leaveEvent(self, event):
        self._mouse_ctrl.handle_leave(event)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if not self._mouse_ctrl.handle_press(event):
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._mouse_ctrl.handle_move(event):
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self._mouse_ctrl.handle_release(event):
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if not self._mouse_ctrl.handle_double_click(event):
            super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        if event.key() == Qt.Key_Delete and self._selected_ann_ids:
            self.delete_selected_annotations()
            event.accept()
        elif ctrl and shift and event.key() == Qt.Key_C:
            self.copyFastaRequested.emit()
            event.accept()
        elif ctrl and not shift and event.key() == Qt.Key_C:
            self.copySequenceRequested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        if not self.isVisible() or self.height() == 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        self._hit_rects = self._renderer.render(self, painter)
        painter.end()
