# widgets/workspace.py

from __future__ import annotations

from typing import FrozenSet, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout, QScrollBar, QSplitter,
    QVBoxLayout, QWidget,
)

from features.annotation_layer.annotation_layer_widget import AnnotationLayerWidget
from features.annotation_layer.annotation_overlay_item import AnnotationOverlayItem
from features.consensus_row.consensus_row_widget import ConsensusRowWidget
from features.header_viewer.header_spacer_widgets import (
    AnnotationSpacerWidget,
    ConsensusSpacerWidget,
    HeaderPositionSpacerWidget,
    HeaderTopWidget,
)
from features.header_viewer.header_viewer_widget import HeaderViewerWidget
from features.navigation_ruler.navigation_ruler_widget import RulerWidget
from features.position_ruler.position_ruler_widget import SequencePositionRulerWidget
from features.sequence_viewer.sequence_viewer_widget import SequenceViewerWidget
from model.alignment_data_model import AlignmentDataModel
from model.annotation import Annotation
from model.annotation_store import AnnotationStore


class _ScrollSyncGuard:
    def __init__(self) -> None:
        self._locked: bool = False

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
    Yerleşim (yukarıdan aşağıya)
    ──────────────────────────────────────────────
    Sol panel                Sağ panel
    ──────────────────────────────────────────────
    HeaderTopWidget          NavigationRuler
    PosSpacerHeader          PositionRuler
    AnnotationSpacerWidget   AnnotationLayerWidget  ← YENİ
    ConsensusSpacerWidget    ConsensusRowWidget
    HeaderViewerWidget       SequenceViewer + overlay
    ──────────────────────────────────────────────

    AnnotationSpacerWidget yüksekliği, AnnotationLayerWidget ile senkronlu
    tutulur (lane sayısı değiştikçe ikisi birlikte güncellenir).
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

        # --- Modeller ---
        self._model = AlignmentDataModel(parent=self)
        self._annotation_store = AnnotationStore(parent=self)

        # --- Sol panel ---
        self.header_top          = HeaderTopWidget(height=ruler_height, parent=self)
        self.header_pos_spacer   = HeaderPositionSpacerWidget(
            height=pos_ruler_height, parent=self)
        self.annotation_spacer   = AnnotationSpacerWidget(parent=self)
        self.consensus_spacer    = ConsensusSpacerWidget(parent=self)
        self.header_viewer       = HeaderViewerWidget(
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
        self.pos_ruler = SequencePositionRulerWidget(
            self.sequence_viewer, parent=self)

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

        # --- Overlay item → sequence viewer sahnesine ekle ---
        self._overlay_item = AnnotationOverlayItem(store=self._annotation_store)
        self.sequence_viewer.scene.addItem(self._overlay_item)

        # Zoom / scroll değişince overlay geometrisini güncelle
        hbar: QScrollBar = self.sequence_viewer.horizontalScrollBar()
        hbar.rangeChanged.connect(self._sync_overlay_geometry)
        anim = getattr(self.sequence_viewer, "_zoom_animation", None)
        if anim is not None:
            anim.valueChanged.connect(self._sync_overlay_geometry)

        # --- AnnotationLayerWidget yüksekliği değişince spacer'ı senkronla ---
        # resizeEvent hook — QWidget'ta resized sinyali yok, installEventFilter kullanıyoruz
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

        # --- Annotation click → tooltip (Qt tooltip sistemi annotation_layer içinde) ---
        self.annotation_layer.annotationClicked.connect(self._on_annotation_clicked)

        # --- Scroll sync ---
        self._v_scroll_guard = _ScrollSyncGuard()
        self._connect_scroll_sync()

    # ==================================================================
    # EventFilter — annotation_layer yüksekliği değişince spacer sync
    # ==================================================================

    def eventFilter(self, obj, event) -> bool:
        from PyQt5.QtCore import QEvent
        if obj is self.annotation_layer and event.type() == QEvent.Resize:
            self.annotation_spacer.sync_height(self.annotation_layer.height())
        return super().eventFilter(obj, event)

    # ==================================================================
    # Overlay geometri senkronizasyonu
    # ==================================================================

    def _sync_overlay_geometry(self, *_args) -> None:
        """Zoom/scroll değişince overlay'in sahne geometrisini güncelle."""
        scene_rect = self.sequence_viewer.scene.sceneRect()
        cw = float(self.sequence_viewer.current_char_width())
        ch = self.sequence_viewer.char_height
        self._overlay_item.update_geometry(
            scene_rect.width(), scene_rect.height(), cw, ch,
        )

    # ==================================================================
    # Annotation public API
    # ==================================================================

    def add_annotation(self, annotation: Annotation) -> str:
        """
        Annotasyon ekler. id döner.
        Overlay ve layer widget otomatik güncellenir.
        """
        ann_id = self._annotation_store.add(annotation)
        self._sync_overlay_geometry()
        return ann_id

    def remove_annotation(self, annotation_id: str) -> None:
        self._annotation_store.remove(annotation_id)

    def clear_annotations(self) -> None:
        self._annotation_store.clear()

    @property
    def annotation_store(self) -> AnnotationStore:
        return self._annotation_store

    # ==================================================================
    # Annotation click
    # ==================================================================

    def _on_annotation_clicked(self, annotation: Annotation) -> None:
        """
        Şimdilik log. İleride: metadata panel aç, seçimi vurgula vb.
        Dışarıdan override için workspace.annotation_layer.annotationClicked
        sinyaline bağlanılabilir.
        """
        pass

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
        self._sync_overlay_geometry()

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
    # View yeniden inşası
    # ==================================================================

    def _rebuild_views(self) -> None:
        h_scroll = self.sequence_viewer.horizontalScrollBar().value()
        v_scroll = self.sequence_viewer.verticalScrollBar().value()

        self.header_viewer.clear()
        self.sequence_viewer.clear()

        for i, (header, sequence) in enumerate(self._model.all_rows()):
            display_text = f"{i + 1}. {header}"
            item = self.header_viewer.add_header_item(display_text)
            item.set_row_index(i)
            if self.header_viewer._selection.is_selected(i):
                item.set_selected(True)
            self.sequence_viewer.add_sequence(sequence)

        self.ruler.update()
        self._update_header_max_width()
        self._sync_overlay_geometry()

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