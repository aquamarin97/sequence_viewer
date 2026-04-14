# sequence_viewer/features/consensus_row/consensus_drag_controller.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from sequence_viewer.settings.mouse_binding_manager import MouseAction, mouse_binding_manager


@dataclass
class DragGuideUpdate:
    """Drag veya tıklama sonucunda uygulanacak guide ve caret değişikliği."""
    guide_cols: List[int]
    selection: Optional[Tuple[int, int]]   # (lo, hi) incl veya None
    set_caret: Optional[int] = None        # caret kolonu veya None


class ConsensusDragController:
    """Consensus satırındaki drag seçim state'ini yönetir.

    Drag threshold, press/move/release döngüsü ve
    boundary-click guide toggle mantığını içerir.
    """

    def __init__(self, tooltip_manager) -> None:
        self._tooltip = tooltip_manager
        self._press_pos = None
        self._press_col: Optional[int] = None
        self._is_dragging: bool = False

    # ── Durum sorguları ───────────────────────────────────────────────────

    def has_press(self) -> bool:
        return self._press_pos is not None

    def is_dragging(self) -> bool:
        return self._is_dragging

    # ── Press / move / release ────────────────────────────────────────────

    def begin_press(self, pos, scene_col: int) -> None:
        self._press_pos = pos
        self._press_col = scene_col
        self._is_dragging = False

    def should_start_drag(self, pos) -> bool:
        """Threshold aşıldıysa ve henüz drag başlamadıysa True döner."""
        if self._press_pos is None or self._is_dragging:
            return False
        threshold = mouse_binding_manager.drag_threshold("consensus_row")
        return (pos - self._press_pos).manhattanLength() >= threshold

    def start_drag(self) -> None:
        self._is_dragging = True

    def compute_drag_update(
        self, scene_col: int, current_guide_cols: List[int]
    ) -> DragGuideUpdate:
        """Mevcut drag frame için guide güncelleme hesaplar."""
        start = self._press_col
        if start is None:
            return DragGuideUpdate(guide_cols=list(current_guide_cols), selection=None)
        lo, hi = min(start, scene_col), max(start, scene_col)
        if hi > lo:
            return DragGuideUpdate(guide_cols=[lo, hi + 1], selection=(lo, hi))
        return DragGuideUpdate(guide_cols=list(current_guide_cols), selection=None)

    def finalize_drag(
        self,
        drag_action,
        current_selection: Optional[Tuple[int, int]],
        current_guide_cols: List[int],
    ) -> DragGuideUpdate:
        """Drag bitti; kalıcı guide listesini hesaplar."""
        self._tooltip.clear_tooltip()
        self._is_dragging = False
        self._press_pos = None

        if current_selection is None:
            return DragGuideUpdate(guide_cols=list(current_guide_cols), selection=current_selection)
        lo, hi = current_selection
        if hi <= lo:
            return DragGuideUpdate(guide_cols=list(current_guide_cols), selection=current_selection)

        base: List[int] = (
            [] if drag_action == MouseAction.DRAG_SELECT else list(current_guide_cols)
        )
        for boundary in (lo, hi + 1):
            if boundary not in base:
                base.append(boundary)
        return DragGuideUpdate(guide_cols=base, selection=current_selection)

    def finalize_click(
        self, boundary_col: int, click_action, current_guide_cols: List[int]
    ) -> DragGuideUpdate:
        """Drag olmadan tıklama bitti; guide toggle veya set hesaplar."""
        self._press_pos = None
        self._is_dragging = False

        if click_action == MouseAction.NONE:
            return DragGuideUpdate(guide_cols=list(current_guide_cols), selection=None)

        cols = list(current_guide_cols)
        if click_action == MouseAction.GUIDE_TOGGLE:
            if boundary_col in cols:
                cols.remove(boundary_col)
            else:
                cols.append(boundary_col)
            return DragGuideUpdate(guide_cols=cols, selection=None)
        else:
            return DragGuideUpdate(guide_cols=[boundary_col], selection=None, set_caret=boundary_col)

    def cancel(self) -> None:
        self._press_pos = None
        self._is_dragging = False
        self._tooltip.clear_tooltip()
