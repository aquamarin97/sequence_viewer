# widgets/workspace.py
from __future__ import annotations
from typing import Dict, FrozenSet, List, Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QScrollBar, QSplitter, QVBoxLayout, QWidget

from features.annotation_layer.annotation_graphics_item import AnnotationGraphicsItem
from features.annotation_layer.annotation_layer_widget import AnnotationLayerWidget
from features.annotation_layer.annotation_layout_engine import assign_lanes, lane_count
from features.consensus_row.consensus_row_widget import ConsensusRowWidget
from features.header_viewer.header_spacer_widgets import (
    AnnotationSpacerWidget, ConsensusSpacerWidget,
    HeaderPositionSpacerWidget, HeaderTopWidget,
)
from features.header_viewer.header_viewer_widget import HeaderViewerWidget
from features.navigation_ruler.navigation_ruler_widget import RulerWidget
from features.position_ruler.position_ruler_widget import SequencePositionRulerWidget
from features.sequence_viewer.sequence_viewer_widget import SequenceViewerWidget
from model.alignment_data_model import AlignmentDataModel
from settings.scrollbar_style import apply_scrollbar_style
from model.annotation import Annotation
from widgets.row_layout import RowLayout

from widgets.row_layout import (
    PAD_FAR, PAD_NEAR, LANE_GAP,
    strip_height, above_lane_y, below_lane_y,
)
_LANE_HEIGHT = 16


class _ScrollSyncGuard:
    def __init__(self):
        self._locked = False
    def sync(self, target: QScrollBar, value: int):
        if self._locked:
            return
        self._locked = True
        try:
            target.setValue(value)
        finally:
            self._locked = False


class SequenceWorkspaceWidget(QWidget):
    def __init__(self, parent=None, char_width=12.0, char_height=18.0):
        super().__init__(parent)
        row_height = int(round(char_height))

        self._model = AlignmentDataModel(parent=self)
        self._ann_items: Dict[str, List[AnnotationGraphicsItem]] = {}

        # Sol panel
        self.header_top        = HeaderTopWidget(height=28, parent=self)
        self.header_pos_spacer = HeaderPositionSpacerWidget(height=24, parent=self)
        self.annotation_spacer = AnnotationSpacerWidget(parent=self)
        self.consensus_spacer  = ConsensusSpacerWidget(parent=self)
        self.header_viewer     = HeaderViewerWidget(parent=self, row_height=row_height, initial_width=160.0)

        self.left_panel = QWidget(self)
        ll = QVBoxLayout(self.left_panel)
        ll.setContentsMargins(0,0,0,0); ll.setSpacing(0)
        for w in [self.header_top, self.header_pos_spacer,
                  self.annotation_spacer, self.consensus_spacer, self.header_viewer]:
            ll.addWidget(w)

        # Sağ panel
        self.sequence_viewer = SequenceViewerWidget(parent=self, char_width=char_width, char_height=row_height)
        self.sequence_viewer.set_alignment_model(self._model)
        self.ruler     = RulerWidget(self.sequence_viewer, parent=self)
        self.pos_ruler = SequencePositionRulerWidget(self.sequence_viewer, parent=self)
        self.annotation_layer = AnnotationLayerWidget(model=self._model, sequence_viewer=self.sequence_viewer, parent=self)
        self.consensus_row    = ConsensusRowWidget(alignment_model=self._model, sequence_viewer=self.sequence_viewer, parent=self)

        right_panel = QWidget(self)
        rl = QVBoxLayout(right_panel)
        rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)
        for w in [self.ruler, self.pos_ruler, self.annotation_layer,
                  self.consensus_row, self.sequence_viewer]:
            rl.addWidget(w)

        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(right_panel)
        # Başlangıçta dizi yok — eşit bölüm (resize sonrası güncellenir)
        self.splitter.setSizes([500, 500])
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

        ml = QHBoxLayout(self)
        ml.setContentsMargins(0,0,0,0); ml.setSpacing(0)
        ml.addWidget(self.splitter)
        self.setLayout(ml)

        hsb_h = self.sequence_viewer.horizontalScrollBar().sizeHint().height()
        self.header_viewer.setViewportMargins(0, 0, 0, hsb_h)

        # Sinyaller — annotation
        self._model.annotationAdded.connect(self._on_annotation_changed)
        self._model.annotationRemoved.connect(self._on_annotation_changed)
        self._model.annotationUpdated.connect(self._on_annotation_changed)
        self._model.annotationsReset.connect(self._on_annotation_changed)

        self.annotation_layer.annotationClicked.connect(self._on_annotation_layer_clicked)
        self.annotation_layer.annotationDoubleClicked.connect(self._on_annotation_layer_double_clicked)
        self.annotation_layer.installEventFilter(self)
        # annotation_layer __init__ sırasında yüksekliğini set etti;
        # eventFilter henüz bağlı değildi — ilk senkronu elle yap.
        self.annotation_spacer.sync_height(self.annotation_layer.height())

        # Sinyaller — model satır
        self._model.rowAppended.connect(self._on_row_appended)
        self._model.rowRemoved.connect(self._on_row_removed)
        self._model.rowMoved.connect(self._on_row_moved)
        self._model.headerChanged.connect(self._on_header_changed)
        self._model.modelReset.connect(self._on_model_reset)

        # Sinyaller — header view
        self.header_viewer.headerEdited.connect(self._on_header_edited)
        self.header_viewer.rowMoveRequested.connect(self._on_row_move_requested)
        self.header_viewer.rowsDeleteRequested.connect(self._on_rows_delete_requested)
        self.header_viewer.selectionChanged.connect(self._on_selection_changed)

        self._v_scroll_guard = _ScrollSyncGuard()
        self._connect_scroll_sync()

        # Sequence viewer seçimi değişince consensus seçimini temizle
        self.sequence_viewer.selectionChanged.connect(
            self.consensus_row.clear_selection
        )

        anim = getattr(self.sequence_viewer, "_zoom_animation", None)
        if anim is not None:
            anim.valueChanged.connect(self._on_zoom_changed)
        self.sequence_viewer.horizontalScrollBar().rangeChanged.connect(self._on_zoom_changed)

        from settings.theme import theme_manager
        theme_manager.themeChanged.connect(self._on_theme_changed)
        self._on_theme_changed(theme_manager.current)

    # ------------------------------------------------------------------
    # RowLayout
    # ------------------------------------------------------------------
    def _compute_row_layout(self) -> RowLayout:
        ch = self.sequence_viewer.char_height
        above_heights: List[int] = []
        below_heights: List[int] = []
        for record in self._model.all_records():
            above_anns = [a for a in record.annotations if a.type.is_above_sequence()]
            below_anns = [a for a in record.annotations if not a.type.is_above_sequence()]
            above_heights.append(strip_height(lane_count(assign_lanes(above_anns))))
            below_heights.append(strip_height(lane_count(assign_lanes(below_anns))))
        return RowLayout.build(ch, above_heights, below_heights)

    def _apply_layout(self, layout: RowLayout):
        self.sequence_viewer.apply_row_layout(layout)
        self.header_viewer.apply_row_layout(layout)

    # ------------------------------------------------------------------
    # Annotation items
    # ------------------------------------------------------------------
    def _remove_all_ann_items(self):
        scene = self.sequence_viewer.scene
        for items in self._ann_items.values():
            for item in items:
                if item.scene() is not None:
                    scene.removeItem(item)
        self._ann_items.clear()

    def _per_row_lane_assignment(self, flat):
        """
        Her satır için ayrı ayrı assign_lanes çağrılır.
        Üst (above) ve alt (below) annotation'lar bağımsız lane atamasına girer —
        böylece her bölgenin lane sayısı ve şerit yüksekliği ayrı hesaplanır.
        """
        from collections import defaultdict
        above_by_row: dict = defaultdict(list)
        below_by_row: dict = defaultdict(list)
        for row_index, ann in flat:
            if ann.type.is_above_sequence():
                above_by_row[row_index].append(ann)
            else:
                below_by_row[row_index].append(ann)
        result = {}
        for anns in above_by_row.values():
            result.update(assign_lanes(anns))
        for anns in below_by_row.values():
            result.update(assign_lanes(anns))
        return result

    def _rebuild_ann_items(self, layout: RowLayout):
        self._remove_all_ann_items()
        flat = self._model.all_annotations_flat()
        if not flat or layout.row_count == 0:
            return
        assignment = self._per_row_lane_assignment(flat)
        cw    = float(self.sequence_viewer.current_char_width())
        ann_h = float(_LANE_HEIGHT)
        scene = self.sequence_viewer.scene

        for row_index, ann in flat:
            if row_index >= layout.row_count:
                continue
            lane    = assignment.get(ann.id, 0)
            scene_x = ann.start * cw
            if ann.type.is_above_sequence():
                scene_y = float(layout.y_offsets[row_index]) + above_lane_y(lane)
            else:
                scene_y = float(layout.below_y_offsets[row_index]) + below_lane_y(lane)
            item = AnnotationGraphicsItem(
                annotation=ann, row_index=row_index,
                ann_width=ann.length() * cw, ann_height=ann_h,
                on_click=self._on_ann_item_clicked,
                on_double_click=self._on_ann_item_double_clicked,
            )
            item.setPos(scene_x, scene_y)
            scene.addItem(item)
            self._ann_items.setdefault(ann.id, []).append(item)

    def _update_ann_items_geometry(self, layout: RowLayout):
        if not self._ann_items or layout.row_count == 0:
            return
        flat = self._model.all_annotations_flat()
        if not flat:
            return
        assignment = self._per_row_lane_assignment(flat)
        cw    = float(self.sequence_viewer.current_char_width())
        ann_h = float(_LANE_HEIGHT)

        for row_index, ann in flat:
            items = self._ann_items.get(ann.id, [])
            if not items or row_index >= layout.row_count:
                continue
            lane    = assignment.get(ann.id, 0)
            scene_x = ann.start * cw
            if ann.type.is_above_sequence():
                scene_y = float(layout.y_offsets[row_index]) + above_lane_y(lane)
            else:
                scene_y = float(layout.below_y_offsets[row_index]) + below_lane_y(lane)
            for item in items:
                if item.row_index == row_index:
                    item.setPos(scene_x, scene_y)
                    item.update_size(ann.length() * cw, ann_h)

    # ------------------------------------------------------------------
    # Tema & arka plan
    # ------------------------------------------------------------------
    def _on_theme_changed(self, theme) -> None:
        """Tema değişince tüm widget arka planlarını ve scrollbar stilini güncelle."""
        from PyQt5.QtGui import QPalette, QBrush as _B
        from settings.color_styles import color_style_manager
        t_bg = theme.seq_bg
        for widget in (self, self.left_panel, self.splitter):
            p = widget.palette()
            p.setBrush(QPalette.Window, _B(t_bg))
            widget.setAutoFillBackground(True)
            widget.setPalette(p)
        # Nükleotid paletini tema ile senkronize et
        color_style_manager.apply_theme(theme.name)
        # Annotation görsel stillerini tema ile senkronize et
        from settings.annotation_styles import annotation_style_manager as _asm
        _asm.apply_theme(theme.name)
        # Sequence viewer scrollbar'larına tema uyumlu stil uygula
        apply_scrollbar_style(self.sequence_viewer)
        self.update()

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _on_annotation_changed(self, *_):
        layout = self._compute_row_layout()
        self._apply_layout(layout)
        self._rebuild_ann_items(layout)

    def _on_zoom_changed(self, *_):
        layout = self._compute_row_layout()
        self._update_ann_items_geometry(layout)

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if obj is self.annotation_layer and event.type() == QEvent.Resize:
            self.annotation_spacer.sync_height(self.annotation_layer.height())
        return super().eventFilter(obj, event)

    def _on_annotation_layer_clicked(self, annotation: Annotation):
        self.sequence_viewer.set_guide_cols(annotation.start, annotation.end)
        n = self._model.row_count()
        if n > 0:
            self.sequence_viewer.set_visual_selection(0, n-1, annotation.start, annotation.end)
            self.sequence_viewer._model.start_selection(0, annotation.start)
            self.sequence_viewer._model.update_selection(n-1, annotation.end)

    def _on_annotation_layer_double_clicked(self, annotation: Annotation):
        self._do_edit_dialog(annotation, row_index=None)

    def _on_ann_item_clicked(self, annotation: Annotation, row_index: int):
        self.sequence_viewer.set_guide_cols(annotation.start, annotation.end)
        n = self._model.row_count()
        if 0 <= row_index < n:
            self.sequence_viewer.set_visual_selection(row_index, row_index, annotation.start, annotation.end)
            self.sequence_viewer._model.start_selection(row_index, annotation.start)
            self.sequence_viewer._model.update_selection(row_index, annotation.end)

    def _on_ann_item_double_clicked(self, annotation: Annotation, row_index: int):
        self.open_edit_annotation_dialog(annotation)

    # ------------------------------------------------------------------
    # Public annotation API
    # ------------------------------------------------------------------
    def add_annotation(self, row_index: int, annotation: Annotation):
        self._model.add_annotation(row_index, annotation)

    def remove_annotation(self, row_index: int, annotation_id: str):
        self._model.remove_annotation(row_index, annotation_id)

    def clear_annotations(self):
        for i in range(self._model.row_count()):
            try:
                self._model.clear_annotations(i)
            except IndexError:
                pass

    def open_find_motifs_dialog(self):
        from features.dialogs.find_motifs_dialog import FindMotifsDialog
        FindMotifsDialog(model=self._model, parent=self).exec_()

    def open_edit_annotation_dialog(self, annotation: Annotation):
        result = self._model.find_annotation(annotation.id)
        if result is None:
            return
        row_index, _ = result
        self._do_edit_dialog(annotation, row_index=row_index)

    def _do_edit_dialog(self, annotation: Annotation, row_index: Optional[int]):
        from features.dialogs.edit_annotation_dialog import EditAnnotationDialog
        dlg = EditAnnotationDialog(annotation=annotation, parent=self)
        if dlg.exec_() == EditAnnotationDialog.Accepted:
            updated = dlg.result_annotation()
            if updated is None:
                return
            try:
                if row_index is not None:
                    self._model.update_annotation(row_index, updated)
                else:
                    self._model.update_global_annotation(updated)
            except (KeyError, IndexError):
                pass

    @property
    def model(self) -> AlignmentDataModel:
        return self._model

    # ------------------------------------------------------------------
    # View → Model
    # ------------------------------------------------------------------
    def _on_header_edited(self, row_index, new_text):
        try:
            self._model.set_header(row_index, new_text)
        except IndexError:
            pass

    def _on_row_move_requested(self, from_index, to_index):
        try:
            self._model.move_row(from_index, to_index)
        except IndexError:
            pass

    def _on_rows_delete_requested(self, rows: FrozenSet[int]):
        for row in sorted(rows, reverse=True):
            try:
                self.header_viewer._selection.remove_row(row)
                self._model.remove_row(row)
            except IndexError:
                pass

    def _on_selection_changed(self, selected_rows):
        """
        Header satır seçimi değişince sequence viewer'da yatay
        kılavuz çizgileri güncellenir.

        Seçili satır(lar)ın tam yükseklik bloğunu (annotation şeridi
        dahil) üstten ve alttan yatay çizgiyle çerçeveliyoruz.
        """
        if not selected_rows:
            self.sequence_viewer.clear_h_guides()
        else:
            self.sequence_viewer.set_h_guides(frozenset(selected_rows))

    # ------------------------------------------------------------------
    # Model → View
    # ------------------------------------------------------------------
    def _on_row_appended(self, index, header, sequence):
        self.header_viewer.add_header_item(f"{index + 1}. {header}")
        self.sequence_viewer.add_sequence(sequence)
        self.ruler.update()
        self._update_header_max_width()
        layout = self._compute_row_layout()
        self._apply_layout(layout)
        self._rebuild_ann_items(layout)

    def _on_row_removed(self, index):
        self._rebuild_views()

    def _on_row_moved(self, from_index, to_index):
        self.header_viewer._selection.move_row(from_index, to_index)
        self._rebuild_views()

    def _on_header_changed(self, index, new_header):
        if index < 0 or index >= len(self.header_viewer.header_items):
            return
        self.header_viewer.header_items[index]._model.full_text = f"{index + 1}. {new_header}"
        self.header_viewer.header_items[index].update()
        self._update_header_max_width()

    def _on_model_reset(self):
        self._rebuild_views()

    def _rebuild_views(self):
        h_scroll = self.sequence_viewer.horizontalScrollBar().value()
        v_scroll = self.sequence_viewer.verticalScrollBar().value()

        self._remove_all_ann_items()
        self.header_viewer.clear()
        self.sequence_viewer.clear()

        for i, (header, sequence) in enumerate(self._model.all_rows()):
            item = self.header_viewer.add_header_item(f"{i + 1}. {header}")
            item.set_row_index(i)
            if self.header_viewer._selection.is_selected(i):
                item.set_selected(True)
            self.sequence_viewer.add_sequence(sequence)

        layout = self._compute_row_layout()
        self._apply_layout(layout)
        self.ruler.update()
        self._update_header_max_width()
        self._rebuild_ann_items(layout)

        self.sequence_viewer.horizontalScrollBar().setValue(h_scroll)
        self.sequence_viewer.verticalScrollBar().setValue(v_scroll)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_sequence(self, header, sequence):
        self._model.append_row(header, sequence)

    def clear(self):
        self._model.clear()

    def move_row(self, from_index, to_index):
        self._model.move_row(from_index, to_index)

    def set_header(self, index, new_header):
        self._model.set_header(index, new_header)

    def selected_rows(self) -> FrozenSet[int]:
        return self.header_viewer._selection.selected_rows()

    def _connect_scroll_sync(self):
        h_vsb = self.header_viewer.verticalScrollBar()
        s_vsb = self.sequence_viewer.verticalScrollBar()
        s_vsb.valueChanged.connect(lambda v: self._v_scroll_guard.sync(h_vsb, v))
        h_vsb.valueChanged.connect(lambda v: self._v_scroll_guard.sync(s_vsb, v))

    def _on_splitter_moved(self, pos, index):
        sizes = self.splitter.sizes()
        if len(sizes) < 2 or not self.header_viewer.header_items:
            return
        left, right = sizes
        required = self.header_viewer.compute_required_width()
        if left > required:
            total = left + right
            self.splitter.blockSignals(True)
            self.splitter.setSizes([required, max(0, total - required)])
            self.splitter.blockSignals(False)

    def _update_header_max_width(self):
        big = 16_777_215
        if self.header_viewer.header_items:
            req = self.header_viewer.compute_required_width()
            self.header_viewer.setMaximumWidth(req)
            self.left_panel.setMaximumWidth(req)
        else:
            # Dizi yokken: sol ve sağ panel eşit genişliği paylaşır.
            # Header viewer ve sol panel kısıtlamaları kaldır.
            self.header_viewer.setMaximumWidth(big)
            self.left_panel.setMaximumWidth(big)
            # Splitter'ı ortala (bir sonraki show/resize'da geçerli olur)
            total = sum(self.splitter.sizes())
            if total > 0:
                half = total // 2
                self.splitter.blockSignals(True)
                self.splitter.setSizes([half, total - half])
                self.splitter.blockSignals(False)