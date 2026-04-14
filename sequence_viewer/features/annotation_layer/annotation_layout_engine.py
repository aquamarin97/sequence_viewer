# sequence_viewer/features/annotation_layer/annotation_layout_engine.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

from sequence_viewer.model.annotation import Annotation, AnnotationType
from sequence_viewer.workspace.row_layout import above_lane_y, below_lane_y, strip_height


@dataclass(frozen=True)
class AnnotationSideGeometry:
    lane_assignment: Dict[str, int]
    marker_parent_ids: frozenset[str]
    marker_lanes: tuple[int, ...]
    total_lanes: int

    def expanded_parent_lane(self, lane: int) -> int:
        return lane + sum(1 for marker_lane in self.marker_lanes if marker_lane < lane)

    def parent_y(self, lane: int, *, above: bool, lane_height=None) -> int:
        expanded_lane = self.expanded_parent_lane(lane)
        return above_lane_y(expanded_lane, lane_height) if above else below_lane_y(expanded_lane, lane_height)

    def marker_y(self, parent_lane: int, *, above: bool, lane_height=None) -> int:
        expanded_lane = self.expanded_parent_lane(parent_lane) + 1
        return above_lane_y(expanded_lane, lane_height) if above else below_lane_y(expanded_lane, lane_height)


def assign_lanes(annotations):
    assignable = [ann for ann in annotations if ann.type.participates_in_lane_assignment()]
    if not assignable:
        return {}
    sorted_anns = sorted(assignable, key=lambda a: (a.start, -a.length()))
    lane_ends = []
    result = {}
    for ann in sorted_anns:
        placed = False
        for lane_idx, last_end in enumerate(lane_ends):
            if ann.start > last_end + 1:
                lane_ends[lane_idx] = ann.end
                result[ann.id] = lane_idx
                placed = True
                break
        if not placed:
            result[ann.id] = len(lane_ends)
            lane_ends.append(ann.end)
    return result


def lane_count(lane_assignment):
    if not lane_assignment:
        return 0
    return max(lane_assignment.values()) + 1


def build_side_geometry(annotations: Iterable[Annotation]) -> AnnotationSideGeometry:
    anns = list(annotations)
    lane_assignment = assign_lanes(anns)
    marker_parent_ids = frozenset(
        ann.parent_id
        for ann in anns
        if ann.type == AnnotationType.MISMATCH_MARKER and ann.parent_id in lane_assignment
    )
    marker_lanes = tuple(sorted({lane_assignment[parent_id] for parent_id in marker_parent_ids}))
    total_lanes = lane_count(lane_assignment) + len(marker_lanes)
    return AnnotationSideGeometry(
        lane_assignment=lane_assignment,
        marker_parent_ids=marker_parent_ids,
        marker_lanes=marker_lanes,
        total_lanes=total_lanes,
    )


def side_strip_height(annotations: Iterable[Annotation], lane_height=None) -> int:
    return strip_height(build_side_geometry(annotations).total_lanes, lane_height=lane_height)


def partition_annotations_by_side(annotations: Iterable[Annotation]):
    anns = list(annotations)
    parent_by_id = {ann.id: ann for ann in anns if ann.type != AnnotationType.MISMATCH_MARKER}
    above = []
    below = []
    for ann in anns:
        if ann.type == AnnotationType.MISMATCH_MARKER:
            parent = parent_by_id.get(ann.parent_id)
            if parent is not None and parent.type.is_above_sequence():
                above.append(ann)
            else:
                below.append(ann)
        elif ann.type.is_above_sequence():
            above.append(ann)
        else:
            below.append(ann)
    return above, below


