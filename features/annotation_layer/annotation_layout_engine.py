# features/annotation_layer/annotation_layout_engine.py
from __future__ import annotations
from typing import Dict, List
from model.annotation import Annotation

def assign_lanes(annotations):
    if not annotations: return {}
    sorted_anns = sorted(annotations, key=lambda a: (a.start, -a.length()))
    lane_ends = []
    result = {}
    for ann in sorted_anns:
        placed = False
        for lane_idx, last_end in enumerate(lane_ends):
            if ann.start > last_end + 1:
                lane_ends[lane_idx] = ann.end
                result[ann.id] = lane_idx
                placed = True; break
        if not placed:
            result[ann.id] = len(lane_ends)
            lane_ends.append(ann.end)
    return result

def lane_count(lane_assignment):
    if not lane_assignment: return 0
    return max(lane_assignment.values()) + 1
