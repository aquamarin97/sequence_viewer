# sequence_viewer/workspace/coordinators/annotation_presentation.py
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from sequence_viewer.features.annotation_layer.annotation_graphics_item import AnnotationGraphicsItem
from sequence_viewer.features.annotation_layer.annotation_layout_engine import (
    build_side_geometry,
    partition_annotations_by_side,
)
from sequence_viewer.model.annotation import AnnotationType
from sequence_viewer.settings.annotation_styles import annotation_style_manager
from sequence_viewer.workspace.row_layout import RowLayout

if TYPE_CHECKING:
    from sequence_viewer.workspace.context import WorkspaceContext


class WorkspaceAnnotationPresentation:
    def __init__(self, ctx: "WorkspaceContext") -> None:
        self._ctx = ctx
        self.ann_items: dict = {}
        self._selected_ann_ids: set = set()

    # ── Seçim yönetimi ────────────────────────────────────────────────────

    def set_selected_annotation(self, ann_id, ctrl: bool = False) -> None:
        if ctrl:
            if ann_id is None:
                return
            if ann_id in self._selected_ann_ids:
                self._selected_ann_ids.discard(ann_id)
                for item in self.ann_items.get(ann_id, []):
                    item.set_selected_visual(False)
            else:
                self._selected_ann_ids.add(ann_id)
                for item in self.ann_items.get(ann_id, []):
                    item.set_selected_visual(True)
        else:
            for prev_id in list(self._selected_ann_ids):
                for item in self.ann_items.get(prev_id, []):
                    item.set_selected_visual(False)
            self._selected_ann_ids.clear()
            if ann_id is not None:
                self._selected_ann_ids.add(ann_id)
                for item in self.ann_items.get(ann_id, []):
                    item.set_selected_visual(True)

    def clear_annotation_selection(self) -> None:
        for prev_id in list(self._selected_ann_ids):
            for item in self.ann_items.get(prev_id, []):
                item.set_selected_visual(False)
        self._selected_ann_ids.clear()

    # ── Item yönetimi ─────────────────────────────────────────────────────

    def remove_all_ann_items(self) -> None:
        scene = self._ctx.sequence_viewer.scene
        for items in self.ann_items.values():
            for item in items:
                if item.scene() is not None:
                    scene.removeItem(item)
        self.ann_items.clear()

    def per_row_lane_assignment(self, flat):
        above_by_row, below_by_row = defaultdict(list), defaultdict(list)
        per_row = defaultdict(list)
        for row_index, ann in flat:
            per_row[row_index].append(ann)
        for row_index, anns in per_row.items():
            above_anns, below_anns = partition_annotations_by_side(anns)
            above_by_row[row_index].extend(above_anns)
            below_by_row[row_index].extend(below_anns)
        result = {}
        for anns in above_by_row.values():
            result.update(build_side_geometry(anns).lane_assignment)
        for anns in below_by_row.values():
            result.update(build_side_geometry(anns).lane_assignment)
        return result

    def rebuild_ann_items(self, layout: RowLayout) -> None:
        self.remove_all_ann_items()
        flat = self._ctx.model.all_annotations_flat()
        if not flat or layout.row_count == 0:
            return
        assignment = self.per_row_lane_assignment(flat)
        row_sides = {}
        for row_index, _ in flat:
            row_anns = [ann for r, ann in flat if r == row_index]
            row_sides[row_index] = partition_annotations_by_side(row_anns)
        side_geometry = {
            ("above", row_index): build_side_geometry(above_anns)
            for row_index, (above_anns, _) in row_sides.items()
        }
        side_geometry.update(
            {
                ("below", row_index): build_side_geometry(below_anns)
                for row_index, (_, below_anns) in row_sides.items()
            }
        )
        cw = float(self._ctx.sequence_viewer.current_char_width())
        ann_h = float(annotation_style_manager.get_lane_height())
        scene = self._ctx.sequence_viewer.scene
        for row_index, ann in flat:
            if row_index >= layout.row_count:
                continue
            scene_x = ann.start * cw
            parent_lookup = {
                candidate.id: candidate for r_idx, candidate in flat if r_idx == row_index
            }
            parent = parent_lookup.get(ann.parent_id)
            is_above = (
                parent.type.is_above_sequence()
                if ann.type == AnnotationType.MISMATCH_MARKER and parent is not None
                else ann.type.is_above_sequence()
            )
            side_key = ("above", row_index) if is_above else ("below", row_index)
            geometry = side_geometry[side_key]
            lane = assignment.get(ann.id, 0)
            if ann.type == AnnotationType.MISMATCH_MARKER:
                parent_lane = assignment.get(ann.parent_id, 0)
                side_y = geometry.marker_y(parent_lane, above=is_above, lane_height=ann_h)
            else:
                side_y = geometry.parent_y(lane, above=is_above, lane_height=ann_h)
            scene_y = float(
                layout.y_offsets[row_index] if is_above else layout.below_y_offsets[row_index]
            ) + side_y
            item = AnnotationGraphicsItem(
                annotation=ann,
                row_index=row_index,
                ann_width=(
                    cw if ann.type == AnnotationType.MISMATCH_MARKER else ann.length() * cw
                ),
                ann_height=ann_h,
                on_click=self._ctx.action_dialogs.on_ann_item_clicked,
                on_double_click=self._ctx.action_dialogs.on_ann_item_double_clicked,
            )
            item.setPos(scene_x, scene_y)
            scene.addItem(item)
            self.ann_items.setdefault(ann.id, []).append(item)
            if ann.id in self._selected_ann_ids:
                item.set_selected_visual(True)

    def update_ann_items_geometry(self, layout: RowLayout) -> None:
        if not self.ann_items or layout.row_count == 0:
            return
        flat = self._ctx.model.all_annotations_flat()
        if not flat:
            return
        assignment = self.per_row_lane_assignment(flat)
        row_sides = {}
        for row_index, _ in flat:
            row_anns = [ann for r, ann in flat if r == row_index]
            row_sides[row_index] = partition_annotations_by_side(row_anns)
        side_geometry = {
            ("above", row_index): build_side_geometry(above_anns)
            for row_index, (above_anns, _) in row_sides.items()
        }
        side_geometry.update(
            {
                ("below", row_index): build_side_geometry(below_anns)
                for row_index, (_, below_anns) in row_sides.items()
            }
        )
        cw = float(self._ctx.sequence_viewer.current_char_width())
        ann_h = float(annotation_style_manager.get_lane_height())
        for row_index, ann in flat:
            items = self.ann_items.get(ann.id, [])
            if not items or row_index >= layout.row_count:
                continue
            scene_x = ann.start * cw
            parent_lookup = {
                candidate.id: candidate for r_idx, candidate in flat if r_idx == row_index
            }
            parent = parent_lookup.get(ann.parent_id)
            is_above = (
                parent.type.is_above_sequence()
                if ann.type == AnnotationType.MISMATCH_MARKER and parent is not None
                else ann.type.is_above_sequence()
            )
            side_key = ("above", row_index) if is_above else ("below", row_index)
            geometry = side_geometry[side_key]
            lane = assignment.get(ann.id, 0)
            if ann.type == AnnotationType.MISMATCH_MARKER:
                parent_lane = assignment.get(ann.parent_id, 0)
                side_y = geometry.marker_y(parent_lane, above=is_above, lane_height=ann_h)
            else:
                side_y = geometry.parent_y(lane, above=is_above, lane_height=ann_h)
            scene_y = float(
                layout.y_offsets[row_index] if is_above else layout.below_y_offsets[row_index]
            ) + side_y
            for item in items:
                if item.row_index == row_index:
                    item.setPos(scene_x, scene_y)
                    item.update_size(
                        cw if ann.type == AnnotationType.MISMATCH_MARKER else ann.length() * cw,
                        ann_h,
                    )

    # ── Signal handler'ları ───────────────────────────────────────────────

    def on_annotation_changed(self, *_) -> None:
        layout = self._ctx.layout_sync.compute_row_layout()
        self._ctx.layout_sync.apply_layout(layout)
        self.rebuild_ann_items(layout)

    def on_zoom_changed(self, *_) -> None:
        layout = self._ctx.layout_sync.compute_row_layout()
        self.update_ann_items_geometry(layout)
