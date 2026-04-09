# widgets/workspace_annotation_presentation.py
from __future__ import annotations
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List
from features.annotation_layer.annotation_graphics_item import AnnotationGraphicsItem
from features.annotation_layer.annotation_layout_engine import assign_lanes
from settings.annotation_styles import annotation_style_manager
from widgets.row_layout import RowLayout, above_lane_y, below_lane_y

if TYPE_CHECKING:
    from widgets.workspace import SequenceWorkspaceWidget

class WorkspaceAnnotationPresentation:
    def __init__(self, workspace):
        self.workspace = workspace
        self.ann_items = {}
        self._selected_ann_id = None

    def set_selected_annotation(self, ann_id):
        if self._selected_ann_id == ann_id: return
        if self._selected_ann_id is not None:
            for item in self.ann_items.get(self._selected_ann_id, []):
                item.set_selected_visual(False)
        self._selected_ann_id = ann_id
        if ann_id is not None:
            for item in self.ann_items.get(ann_id, []):
                item.set_selected_visual(True)

    def remove_all_ann_items(self):
        scene = self.workspace.sequence_viewer.scene
        for items in self.ann_items.values():
            for item in items:
                if item.scene() is not None: scene.removeItem(item)
        self.ann_items.clear()

    def per_row_lane_assignment(self, flat):
        above_by_row, below_by_row = defaultdict(list), defaultdict(list)
        for row_index, ann in flat:
            if ann.type.is_above_sequence(): above_by_row[row_index].append(ann)
            else: below_by_row[row_index].append(ann)
        result = {}
        for anns in above_by_row.values(): result.update(assign_lanes(anns))
        for anns in below_by_row.values(): result.update(assign_lanes(anns))
        return result

    def rebuild_ann_items(self, layout):
        self.remove_all_ann_items()
        flat = self.workspace.model.all_annotations_flat()
        if not flat or layout.row_count == 0: return
        assignment = self.per_row_lane_assignment(flat)
        cw = float(self.workspace.sequence_viewer.current_char_width())
        ann_h = float(annotation_style_manager.get_lane_height()); scene = self.workspace.sequence_viewer.scene
        for row_index, ann in flat:
            if row_index >= layout.row_count: continue
            lane = assignment.get(ann.id, 0); scene_x = ann.start * cw
            if ann.type.is_above_sequence(): scene_y = float(layout.y_offsets[row_index]) + above_lane_y(lane)
            else: scene_y = float(layout.below_y_offsets[row_index]) + below_lane_y(lane)
            item = AnnotationGraphicsItem(annotation=ann, row_index=row_index, ann_width=ann.length()*cw, ann_height=ann_h,
                on_click=self.workspace._on_ann_item_clicked, on_double_click=self.workspace._on_ann_item_double_clicked)
            item.setPos(scene_x, scene_y); scene.addItem(item)
            self.ann_items.setdefault(ann.id, []).append(item)
            if ann.id == self._selected_ann_id:
                item.set_selected_visual(True)

    def update_ann_items_geometry(self, layout):
        if not self.ann_items or layout.row_count == 0: return
        flat = self.workspace.model.all_annotations_flat()
        if not flat: return
        assignment = self.per_row_lane_assignment(flat)
        cw = float(self.workspace.sequence_viewer.current_char_width()); ann_h = float(annotation_style_manager.get_lane_height())
        for row_index, ann in flat:
            items = self.ann_items.get(ann.id, [])
            if not items or row_index >= layout.row_count: continue
            lane = assignment.get(ann.id, 0); scene_x = ann.start * cw
            if ann.type.is_above_sequence(): scene_y = float(layout.y_offsets[row_index]) + above_lane_y(lane)
            else: scene_y = float(layout.below_y_offsets[row_index]) + below_lane_y(lane)
            for item in items:
                if item.row_index == row_index:
                    item.setPos(scene_x, scene_y); item.update_size(ann.length()*cw, ann_h)

    def on_annotation_changed(self, *_):
        layout = self.workspace._compute_row_layout()
        self.workspace._apply_layout(layout); self.rebuild_ann_items(layout)

    def on_zoom_changed(self, *_):
        layout = self.workspace._compute_row_layout()
        self.update_ann_items_geometry(layout)
