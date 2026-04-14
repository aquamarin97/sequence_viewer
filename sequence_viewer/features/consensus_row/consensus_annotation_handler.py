# sequence_viewer/features/consensus_row/consensus_annotation_handler.py
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, FrozenSet, List

from sequence_viewer.model.annotation import AnnotationType

if TYPE_CHECKING:
    from sequence_viewer.model.alignment_data_model import AlignmentDataModel


@dataclass
class AnnotationSelectResult:
    """_select_annotation_range hesabının değişmez sonucu.

    Widget bu nesneyi alır ve kendi state'ine uygular.
    Hiçbir yan etki yoktur.
    """
    selected_ids: FrozenSet
    selection_ranges: List
    guide_cols: List[int]
    dim_start: int
    dim_end: int
    clear_workspace: bool        # workspaceAnnotationClearRequested.emit() gerekli mi?
    refresh_coordinator: bool    # coordinatorRefreshRequested.emit() gerekli mi?


class ConsensusAnnotationHandler:
    """Annotation seçim mantığını saf hesaplama olarak kapsüller.

    Widget state'ini değiştirmez — AnnotationSelectResult döndürür,
    widget da kendi state'ini günceller.
    """

    def __init__(self, alignment_model: "AlignmentDataModel") -> None:
        self._model = alignment_model

    def compute_select(
        self,
        ann,
        ctrl: bool,
        current_ids: FrozenSet,
    ) -> AnnotationSelectResult:
        if ctrl:
            return self._compute_additive(ann, current_ids)
        return self._compute_single(ann)

    # ── İç hesaplamalar ──────────────────────────────────────────────────

    def _compute_additive(self, ann, current_ids: FrozenSet) -> AnnotationSelectResult:
        """Ctrl+tıklama: mevcut seçime ekle veya çıkar."""
        new_ids: FrozenSet = (
            current_ids - {ann.id}
            if ann.id in current_ids
            else current_ids | {ann.id}
        )
        ann_map = {
            a.id: a
            for a in (
                self._model.consensus_annotations if self._model.is_aligned else []
            )
        }
        selected_anns = [ann_map[aid] for aid in new_ids if aid in ann_map]
        ranges = (
            [
                (a.start, a.start + 1)
                if a.type == AnnotationType.MISMATCH_MARKER
                else (a.start, a.end + 1)
                for a in selected_anns
            ]
            if selected_anns
            else []
        )
        return AnnotationSelectResult(
            selected_ids=new_ids,
            selection_ranges=ranges,
            guide_cols=[],
            dim_start=0,
            dim_end=0,
            clear_workspace=False,
            refresh_coordinator=True,
        )

    def _compute_single(self, ann) -> AnnotationSelectResult:
        """Tekil tıklama: sadece bu annotation'ı seç."""
        is_marker = ann.type == AnnotationType.MISMATCH_MARKER
        range_end = ann.start + 1 if is_marker else ann.end + 1
        return AnnotationSelectResult(
            selected_ids=frozenset({ann.id}),
            selection_ranges=[(ann.start, range_end)],
            guide_cols=[ann.start] if is_marker else [ann.start, ann.end + 1],
            dim_start=ann.start,
            dim_end=range_end,
            clear_workspace=True,
            refresh_coordinator=False,
        )
