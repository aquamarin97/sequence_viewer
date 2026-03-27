# widgets/workspace.py

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout, QScrollBar, QSplitter,
    QVBoxLayout, QWidget,
)

from features.annotation_layer.annotation_graphics_item import AnnotationGraphicsItem
from features.annotation_layer.annotation_layer_widget import AnnotationLayerWidget
from features.annotation_layer.annotation_layout_engine import (
    assign_lanes, lane_count,
)
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
from model.annotation import Annotation
from model.annotation_store import AnnotationStore

# Lane sabitleri
_LANE_HEIGHT  = 16
_LANE_PADDING =  2


class _ScrollSyncGuard:
    def __init__(self) -> None:
        self._locked = False

    def sync(self, target: QScrollBar, value: int) -> None:
        if self._locked:
            return
        self._locked = True
        try:
            target.setValue(value)
        finally:
            self._locked = False


class SequenceWorkspaceWidget(QWidget):
    """
    v3 workspace.

    Annotation item mimarisi
    ------------------------
    Her (annotation, row_index) çifti için bağımsız AnnotationGraphicsItem.
    - seq_indices=None → tüm satırlarda birer item
    - seq_indices=[0,2] → sadece o satırlarda item
    - Her item bağımsız tıklanabilir → doğru satır seçimi
    - store veya model değişince _rebuild_ann_items() çağrılır

    Header hizalaması
    -----------------
    set_annot_height(h) → header_viewer'a iletilir.
    HeaderRowItem yüksekliği = annot_height + char_height.
    Font boyutu asla değişmez.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        char_width: float = 12.0,
        char_height: float = 18.0,
    ) -> None:
        super().__init__(parent)

        row_height       = int(round(char_height))
        ruler_height     = 28
        pos_ruler_height = 24

        self._model            = AlignmentDataModel(parent=self)
        self._annotation_store = AnnotationStore(parent=self)

        # Bireysel annotation item'ları: ann_id → List[AnnotationGraphicsItem]
        self._ann_items: Dict[str, List[AnnotationGraphicsItem]] = {}

        # --- Sol panel ---
        self.header_top        = HeaderTopWidget(height=ruler_height, parent=self)
        self.header_pos_spacer = HeaderPositionSpacerWidget(height=pos_ruler_height, parent=self)
        self.annotation_spacer = AnnotationSpacerWidget(parent=self)
        self.consensus_spacer  = ConsensusSpacerWidget(parent=self)
        self.header_viewer     = HeaderViewerWidget(
            parent=self, row_height=row_height, initial_width=160.0)

        self.left_panel = QWidget(self)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(self.header_top)
        left_layout.addWidget(self.header_pos_spacer)
        left_layout.addWidget(self.annotation_spacer)
        left_layout.addWidget(self.consensus_spacer)
        left_layout.addWidget(self.header_viewer)

        # --- Sağ panel ---
        self.sequence_viewer = SequenceViewerWidget(
            parent=self, char_width=char_width, char_height=row_height)
        self.ruler     = RulerWidget(self.sequence_viewer, parent=self)
        self.pos_ruler = SequencePositionRulerWidget(self.sequence_viewer, parent=self)

        self.annotation_layer = AnnotationLayerWidget(
            store=self._annotation_store,
            sequence_viewer=self.sequence_viewer,
            parent=self,
        )
        self.consensus_row = ConsensusRowWidget(
            alignment_model=self._model,
            sequence_viewer=self.sequence_viewer,
            parent=self,
        )

        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.ruler)
        right_layout.addWidget(self.pos_ruler)
        right_layout.addWidget(self.annotation_layer)
        right_layout.addWidget(self.consensus_row)
        right_layout.addWidget(self.sequence_viewer)

        # --- Splitter ---
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([200, 800])
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

        hsb_h = self.sequence_viewer.horizontalScrollBar().sizeHint().height()
        self.header_viewer.setViewportMargins(0, 0, 0, hsb_h)

        # --- Store → item rebuild ---
        self._annotation_store.annotationAdded.connect(self._on_store_changed)
        self._annotation_store.annotationRemoved.connect(self._on_store_changed)
        self._annotation_store.annotationUpdated.connect(self._on_store_changed)
        self._annotation_store.storeReset.connect(self._on_store_changed)

        # --- Annotation layer sinyalleri ---
        self.annotation_layer.annotationClicked.connect(self._on_annotation_layer_clicked)
        self.annotation_layer.annotationDoubleClicked.connect(self.open_edit_annotation_dialog)

        # --- Annotation spacer height sync ---
        self.annotation_layer.installEventFilter(self)

        # --- Model → View ---
        self._model.rowAppended.connect(self._on_row_appended)
        self._model.rowRemoved.connect(self._on_row_removed)
        self._model.rowMoved.connect(self._on_row_moved)
        self._model.headerChanged.connect(self._on_header_changed)
        self._model.modelReset.connect(self._on_model_reset)

        # --- View → Model ---
        self.header_viewer.headerEdited.connect(self._on_header_edited)
        self.header_viewer.rowMoveRequested.connect(self._on_row_move_requested)
        self.header_viewer.rowsDeleteRequested.connect(self._on_rows_delete_requested)
        self.header_viewer.selectionChanged.connect(self._on_selection_changed)

        # --- Scroll sync ---
        self._v_scroll_guard = _ScrollSyncGuard()
        self._connect_scroll_sync()

        # --- Zoom → item geometri güncelle ---
        anim = getattr(self.sequence_viewer, "_zoom_animation", None)
        if anim is not None:
            anim.valueChanged.connect(self._on_zoom_changed)
        hbar: QScrollBar = self.sequence_viewer.horizontalScrollBar()
        hbar.rangeChanged.connect(self._on_zoom_changed)

    # ==================================================================
    # Per-row annotation height hesaplama
    # ==================================================================

    def _compute_per_row_annot_height(self) -> int:
        annotations = self._annotation_store.all()
        if not annotations:
            return 0
        n = lane_count(assign_lanes(annotations))
        return n * (_LANE_HEIGHT + _LANE_PADDING) + _LANE_PADDING if n > 0 else 0

    def _apply_annot_height(self, h: int) -> None:
        """Annotation yüksekliğini hem sequence viewer hem header viewer'a uygular."""
        self.sequence_viewer.set_per_row_annot_height(h)
        self.header_viewer.set_annot_height(h)

    # ==================================================================
    # Bireysel annotation item yönetimi
    # ==================================================================

    def _remove_all_ann_items(self) -> None:
        """Sahnedeki tüm annotation item'larını kaldır."""
        scene = self.sequence_viewer.scene
        for items in self._ann_items.values():
            for item in items:
                if item.scene() is not None:
                    scene.removeItem(item)
        self._ann_items.clear()

    def _rebuild_ann_items(self) -> None:
        """
        Store ve model state'ine göre tüm annotation item'larını yeniden oluşturur.

        Her (annotation, row_index) çifti için ayrı AnnotationGraphicsItem.
        """
        self._remove_all_ann_items()

        annotations  = self._annotation_store.all()
        if not annotations:
            return

        row_count    = self._model.row_count()
        if row_count == 0:
            return

        assignment   = assign_lanes(annotations)
        cw           = float(self.sequence_viewer.current_char_width())
        ch           = self.sequence_viewer.char_height
        per_row_h    = self._compute_per_row_annot_height()
        row_stride   = per_row_h + ch
        ann_h        = float(_LANE_HEIGHT)

        scene = self.sequence_viewer.scene

        for ann in annotations:
            # Hangi satırlar?
            if ann.seq_indices is None:
                rows = range(row_count)
            else:
                rows = [r for r in ann.seq_indices if 0 <= r < row_count]

            lane      = assignment.get(ann.id, 0)
            ann_w     = ann.length() * cw
            scene_x   = ann.start * cw
            lane_y_off = lane * (_LANE_HEIGHT + _LANE_PADDING) + _LANE_PADDING

            items_for_ann: List[AnnotationGraphicsItem] = []

            for row in rows:
                # Y: satırın annotation şeridindeki lane pozisyonu
                scene_y = row * row_stride + lane_y_off

                item = AnnotationGraphicsItem(
                    annotation     = ann,
                    row_index      = row,
                    ann_width      = ann_w,
                    ann_height     = ann_h,
                    on_click       = self._on_ann_item_clicked,
                    on_double_click= self._on_ann_item_double_clicked,
                )
                item.setPos(scene_x, scene_y)
                scene.addItem(item)
                items_for_ann.append(item)

            self._ann_items[ann.id] = items_for_ann

    def _update_ann_items_geometry(self) -> None:
        """Zoom değişince item pozisyonlarını ve boyutlarını günceller."""
        if not self._ann_items:
            return

        annotations = self._annotation_store.all()
        if not annotations:
            return

        row_count  = self._model.row_count()
        assignment = assign_lanes(annotations)
        cw         = float(self.sequence_viewer.current_char_width())
        per_row_h  = self._compute_per_row_annot_height()
        row_stride = per_row_h + self.sequence_viewer.char_height
        ann_h      = float(_LANE_HEIGHT)

        for ann in annotations:
            items = self._ann_items.get(ann.id, [])
            if not items:
                continue

            lane      = assignment.get(ann.id, 0)
            ann_w     = ann.length() * cw
            scene_x   = ann.start * cw
            lane_y_off = lane * (_LANE_HEIGHT + _LANE_PADDING) + _LANE_PADDING

            rows = (
                range(row_count) if ann.seq_indices is None
                else [r for r in ann.seq_indices if 0 <= r < row_count]
            )

            for item, row in zip(items, rows):
                scene_y = row * row_stride + lane_y_off
                item.setPos(scene_x, scene_y)
                item.update_size(ann_w, ann_h)

    # ==================================================================
    # Store ve zoom callback'leri
    # ==================================================================

    def _on_store_changed(self, *_args) -> None:
        h = self._compute_per_row_annot_height()
        self._apply_annot_height(h)
        self._rebuild_ann_items()

    def _on_zoom_changed(self, *_args) -> None:
        self._update_ann_items_geometry()

    # ==================================================================
    # EventFilter
    # ==================================================================

    def eventFilter(self, obj, event) -> bool:
        from PyQt5.QtCore import QEvent
        if obj is self.annotation_layer and event.type() == QEvent.Resize:
            self.annotation_spacer.sync_height(self.annotation_layer.height())
        return super().eventFilter(obj, event)

    # ==================================================================
    # Annotation tıklama
    # ==================================================================

    def _on_annotation_layer_clicked(self, annotation: Annotation) -> None:
        """Üst şerit: sadece consensus alanını seç, kılavuz çizgileri göster."""
        self.sequence_viewer.set_guide_cols(annotation.start, annotation.end)
        n = self._model.row_count()
        if n > 0:
            self.sequence_viewer.set_visual_selection(
                0, n - 1, annotation.start, annotation.end
            )
            self.sequence_viewer._model.start_selection(0, annotation.start)
            self.sequence_viewer._model.update_selection(n - 1, annotation.end)

    def _on_ann_item_clicked(self, annotation: Annotation, row_index: int) -> None:
        """Bireysel item: sadece o satırı seç, kılavuz çizgileri göster."""
        self.sequence_viewer.set_guide_cols(annotation.start, annotation.end)
        n = self._model.row_count()
        if 0 <= row_index < n:
            self.sequence_viewer.set_visual_selection(
                row_index, row_index, annotation.start, annotation.end
            )
            self.sequence_viewer._model.start_selection(row_index, annotation.start)
            self.sequence_viewer._model.update_selection(row_index, annotation.end)

    def _on_ann_item_double_clicked(
        self, annotation: Annotation, row_index: int
    ) -> None:
        self.open_edit_annotation_dialog(annotation)

    # ==================================================================
    # Annotation API
    # ==================================================================

    def add_annotation(self, annotation: Annotation) -> str:
        return self._annotation_store.add(annotation)

    def remove_annotation(self, annotation_id: str) -> None:
        self._annotation_store.remove(annotation_id)

    def clear_annotations(self) -> None:
        self._annotation_store.clear()

    def open_find_motifs_dialog(self) -> None:
        from features.dialogs.find_motifs_dialog import FindMotifsDialog
        sequences = [seq for _, seq in self._model.all_rows()]
        dlg = FindMotifsDialog(
            store=self._annotation_store,
            sequences=sequences,
            parent=self,
        )
        dlg.exec_()

    def open_edit_annotation_dialog(self, annotation: Annotation) -> None:
        from features.dialogs.edit_annotation_dialog import EditAnnotationDialog
        dlg = EditAnnotationDialog(annotation=annotation, parent=self)
        if dlg.exec_() == EditAnnotationDialog.Accepted:
            updated = dlg.result_annotation()
            if updated is not None:
                try:
                    self._annotation_store.update(updated)
                except KeyError:
                    pass

    @property
    def annotation_store(self) -> AnnotationStore:
        return self._annotation_store

    # ==================================================================
    # View → Model
    # ==================================================================

    def _on_header_edited(self, row_index: int, new_text: str) -> None:
        try:
            self._model.set_header(row_index, new_text)
        except IndexError:
            pass

    def _on_row_move_requested(self, from_index: int, to_index: int) -> None:
        try:
            self._model.move_row(from_index, to_index)
        except IndexError:
            pass

    def _on_rows_delete_requested(self, rows: FrozenSet[int]) -> None:
        for row in sorted(rows, reverse=True):
            try:
                self.header_viewer._selection.remove_row(row)
                self._model.remove_row(row)
            except IndexError:
                pass

    def _on_selection_changed(self, selected_rows: FrozenSet[int]) -> None:
        pass

    # ==================================================================
    # Model → View
    # ==================================================================

    def _on_row_appended(self, index: int, header: str, sequence: str) -> None:
        display_text = f"{index + 1}. {header}"
        self.header_viewer.add_header_item(display_text)
        self.sequence_viewer.add_sequence(sequence)
        self.ruler.update()
        self._update_header_max_width()
        self._rebuild_ann_items()

    def _on_row_removed(self, index: int) -> None:
        self._rebuild_views()

    def _on_row_moved(self, from_index: int, to_index: int) -> None:
        self.header_viewer._selection.move_row(from_index, to_index)
        self._rebuild_views()

    def _on_header_changed(self, index: int, new_header: str) -> None:
        if index < 0 or index >= len(self.header_viewer.header_items):
            return
        display_text = f"{index + 1}. {new_header}"
        item = self.header_viewer.header_items[index]
        item._model.full_text = display_text
        item.update()
        self._update_header_max_width()

    def _on_model_reset(self) -> None:
        self._rebuild_views()

    # ==================================================================
    # View rebuild
    # ==================================================================

    def _rebuild_views(self) -> None:
        h_scroll = self.sequence_viewer.horizontalScrollBar().value()
        v_scroll = self.sequence_viewer.verticalScrollBar().value()

        # Ann item'ları sahneden temizle (scene.clear()'dan önce)
        self._remove_all_ann_items()

        self.header_viewer.clear()
        self.sequence_viewer.clear()

        h = self._compute_per_row_annot_height()
        self._apply_annot_height(h)

        for i, (header, sequence) in enumerate(self._model.all_rows()):
            display_text = f"{i + 1}. {header}"
            item = self.header_viewer.add_header_item(display_text)
            item.set_row_index(i)
            if self.header_viewer._selection.is_selected(i):
                item.set_selected(True)
            self.sequence_viewer.add_sequence(sequence)

        self.ruler.update()
        self._update_header_max_width()
        self._rebuild_ann_items()

        self.sequence_viewer.horizontalScrollBar().setValue(h_scroll)
        self.sequence_viewer.verticalScrollBar().setValue(v_scroll)

    # ==================================================================
    # Public API
    # ==================================================================

    def add_sequence(self, header: str, sequence: str) -> None:
        self._model.append_row(header, sequence)

    def clear(self) -> None:
        self._model.clear()

    def move_row(self, from_index: int, to_index: int) -> None:
        self._model.move_row(from_index, to_index)

    def set_header(self, index: int, new_header: str) -> None:
        self._model.set_header(index, new_header)

    def selected_rows(self) -> FrozenSet[int]:
        return self.header_viewer._selection.selected_rows()

    @property
    def model(self) -> AlignmentDataModel:
        return self._model

    # ==================================================================
    # Scroll sync
    # ==================================================================

    def _connect_scroll_sync(self) -> None:
        h_vsb: QScrollBar = self.header_viewer.verticalScrollBar()
        s_vsb: QScrollBar = self.sequence_viewer.verticalScrollBar()
        s_vsb.valueChanged.connect(lambda v: self._v_scroll_guard.sync(h_vsb, v))
        h_vsb.valueChanged.connect(lambda v: self._v_scroll_guard.sync(s_vsb, v))

    # ==================================================================
    # Splitter
    # ==================================================================

    def _on_splitter_moved(self, pos: int, index: int) -> None:
        sizes = self.splitter.sizes()
        if len(sizes) < 2 or not self.header_viewer.header_items:
            return
        left, right = sizes[0], sizes[1]
        required    = self.header_viewer.compute_required_width()
        if left > required:
            total = left + right
            left  = required
            right = max(0, total - left)
            self.splitter.blockSignals(True)
            self.splitter.setSizes([left, right])
            self.splitter.blockSignals(False)

    def _update_header_max_width(self) -> None:
        if self.header_viewer.header_items:
            required = self.header_viewer.compute_required_width()
            self.header_viewer.setMaximumWidth(required)
            self.left_panel.setMaximumWidth(required)
        else:
            big = 16_777_215
            self.header_viewer.setMaximumWidth(big)
            self.left_panel.setMaximumWidth(big)