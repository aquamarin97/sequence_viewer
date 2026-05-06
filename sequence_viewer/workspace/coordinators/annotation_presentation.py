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
        # Cache: ann_id → (row_index, scene_y, is_marker, start, length)
        # Rebuilt in rebuild_ann_items; allows on_zoom_changed to skip
        # compute_row_layout() + lane assignment entirely during zoom.
        self._ann_geo_cache: dict = {}

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
        self._ann_geo_cache.clear()

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

    @staticmethod
    def _build_side_geometry_maps(per_row: dict) -> tuple[dict, dict, dict]:
        """O(N) helper: returns (row_sides, side_geometry, per_row_lookup)."""
        row_sides = {row_index: partition_annotations_by_side(anns)
                     for row_index, anns in per_row.items()}
        side_geometry: dict = {}
        for row_index, (above_anns, below_anns) in row_sides.items():
            side_geometry[("above", row_index)] = build_side_geometry(above_anns)
            side_geometry[("below", row_index)] = build_side_geometry(below_anns)
        per_row_lookup = {row_index: {ann.id: ann for ann in anns}
                          for row_index, anns in per_row.items()}
        return row_sides, side_geometry, per_row_lookup

    def rebuild_ann_items(self, layout: RowLayout) -> None:
        self.remove_all_ann_items()
        flat = self._ctx.model.all_annotations_flat()
        if not flat or layout.row_count == 0:
            return

        # O(N) grouping — avoids O(N²) nested list comprehension
        per_row: dict = defaultdict(list)
        for row_index, ann in flat:
            per_row[row_index].append(ann)

        assignment = self.per_row_lane_assignment(flat)
        _row_sides, side_geometry, per_row_lookup = self._build_side_geometry_maps(per_row)

        cw = float(self._ctx.sequence_viewer.current_char_width())
        ann_h = float(annotation_style_manager.get_lane_height())
        scene = self._ctx.sequence_viewer.scene

        for row_index, ann in flat:
            if row_index >= layout.row_count:
                continue

            parent_lookup = per_row_lookup[row_index]
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

            is_marker = ann.type == AnnotationType.MISMATCH_MARKER
            scene_x = ann.start * cw
            ann_width = cw if is_marker else ann.length() * cw

            # Persist Y offsets so on_zoom_changed can skip recomputation
            self._ann_geo_cache[ann.id] = (row_index, scene_y, is_marker, ann.start, ann.length())

            item = AnnotationGraphicsItem(
                annotation=ann,
                row_index=row_index,
                ann_width=ann_width,
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
        cw = float(self._ctx.sequence_viewer.current_char_width())
        ann_h = float(annotation_style_manager.get_lane_height())
        if self._ann_geo_cache:
            self._apply_positions_from_cache(cw, ann_h)
            return

        # Fallback (cache not populated): O(N) full recompute
        flat = self._ctx.model.all_annotations_flat()
        if not flat:
            return
        per_row: dict = defaultdict(list)
        for row_index, ann in flat:
            per_row[row_index].append(ann)
        assignment = self.per_row_lane_assignment(flat)
        _row_sides, side_geometry, per_row_lookup = self._build_side_geometry_maps(per_row)

        for row_index, ann in flat:
            items = self.ann_items.get(ann.id, [])
            if not items or row_index >= layout.row_count:
                continue
            parent_lookup = per_row_lookup[row_index]
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
            scene_x = ann.start * cw
            for item in items:
                if item.row_index == row_index:
                    item.setPos(scene_x, scene_y)
                    item.update_size(
                        cw if ann.type == AnnotationType.MISMATCH_MARKER else ann.length() * cw,
                        ann_h,
                    )

    def _apply_positions_from_cache(self, cw: float, ann_h: float) -> None:
        """O(N) fast path: uses cached Y offsets, only recomputes scene_x."""
        for ann_id, (row_index, scene_y, is_marker, start, length) in self._ann_geo_cache.items():
            items = self.ann_items.get(ann_id, [])
            if not items:
                continue
            scene_x = start * cw
            width = cw if is_marker else length * cw
            for item in items:
                if item.row_index == row_index:
                    item.setPos(scene_x, scene_y)
                    item.update_size(width, ann_h)

    # ── Signal handler'ları ───────────────────────────────────────────────

    def on_annotation_changed(self, *_) -> None:
        layout = self._ctx.layout_sync.compute_row_layout()
        self._ctx.layout_sync.apply_layout(layout)
        self.rebuild_ann_items(layout)

    def on_zoom_changed(self, *_) -> None:
        if self._ann_geo_cache:
            # Fast path: Y positions cached, compute_row_layout() not needed
            cw = float(self._ctx.sequence_viewer.current_char_width())
            ann_h = float(annotation_style_manager.get_lane_height())
            self._apply_positions_from_cache(cw, ann_h)
        else:
            layout = self._ctx.layout_sync.compute_row_layout()
            self.update_ann_items_geometry(layout)
