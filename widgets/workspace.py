# widgets/workspace.py
"""
MODIFIED:
- ConsensusSpacerWidget click → select all consensus
- ConsensusSpacerWidget double-click → edit consensus label
- Consensus row visibility synced with is_aligned
- Consensus spacer visibility synced with consensus row
"""
from __future__ import annotations
from typing import FrozenSet
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QSplitter, QVBoxLayout, QWidget
from features.annotation_layer.annotation_layer_widget import AnnotationLayerWidget
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
from settings.scrollbar_style import apply_scrollbar_style
from widgets import workspace_action_dialog_coordinator
from widgets import workspace_annotation_presentation
from widgets import workspace_layout_scroll_sync

class SequenceWorkspaceWidget(QWidget):
    def __init__(self, parent=None, char_width=12.0, char_height=18.0):
        super().__init__(parent)
        row_height = int(round(char_height))
        self._model = AlignmentDataModel(parent=self)

        # Sol panel
        self.header_top = HeaderTopWidget(height=28, parent=self)
        self.header_pos_spacer = HeaderPositionSpacerWidget(height=24, parent=self)
        self.annotation_spacer = AnnotationSpacerWidget(parent=self)
        self.consensus_spacer = ConsensusSpacerWidget(parent=self)
        self.header_viewer = HeaderViewerWidget(parent=self, row_height=row_height, initial_width=160.0)

        self.left_panel = QWidget(self)
        ll = QVBoxLayout(self.left_panel)
        ll.setContentsMargins(0,0,0,0); ll.setSpacing(0)
        for w in [self.header_top, self.header_pos_spacer, self.annotation_spacer,
                  self.consensus_spacer, self.header_viewer]:
            ll.addWidget(w)

        # Sağ panel
        self.sequence_viewer = SequenceViewerWidget(parent=self, char_width=char_width, char_height=row_height)
        self.sequence_viewer.set_alignment_model(self._model)
        self.ruler = RulerWidget(self.sequence_viewer, parent=self)
        self.pos_ruler = SequencePositionRulerWidget(self.sequence_viewer, parent=self)
        self.annotation_layer = AnnotationLayerWidget(model=self._model, sequence_viewer=self.sequence_viewer, parent=self)
        self.consensus_row = ConsensusRowWidget(alignment_model=self._model, sequence_viewer=self.sequence_viewer, parent=self)

        right_panel = QWidget(self)
        rl = QVBoxLayout(right_panel)
        rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)
        for w in [self.ruler, self.pos_ruler, self.annotation_layer, self.consensus_row, self.sequence_viewer]:
            rl.addWidget(w)

        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.addWidget(self.left_panel); self.splitter.addWidget(right_panel)
        self.splitter.setSizes([130, 500])

        ml = QHBoxLayout(self)
        ml.setContentsMargins(0,0,0,0); ml.setSpacing(0)
        ml.addWidget(self.splitter); self.setLayout(ml)

        hsb_h = self.sequence_viewer.horizontalScrollBar().sizeHint().height()
        self.header_viewer.setViewportMargins(0, 0, 0, hsb_h)

        # Coordinators
        self._layout_sync = workspace_layout_scroll_sync.WorkspaceLayoutScrollSync(self)
        self._annotation_presentation = workspace_annotation_presentation.WorkspaceAnnotationPresentation(self)
        self._action_dialogs = workspace_action_dialog_coordinator.WorkspaceActionDialogCoordinator(self)

        self.splitter.splitterMoved.connect(self._on_splitter_moved)

        # Sinyaller — annotation
        self._model.annotationAdded.connect(self._on_annotation_changed)
        self._model.annotationRemoved.connect(self._on_annotation_changed)
        self._model.annotationUpdated.connect(self._on_annotation_changed)
        self._model.annotationsReset.connect(self._on_annotation_changed)

        self.annotation_layer.annotationClicked.connect(self._on_annotation_layer_clicked)
        self.annotation_layer.annotationDoubleClicked.connect(self._on_annotation_layer_double_clicked)
        self.annotation_layer.installEventFilter(self)
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

        # Sinyaller — consensus spacer
        self.consensus_spacer.clicked.connect(self._on_consensus_spacer_clicked)

        # Alignment state → consensus visibility
        self._model.alignmentStateChanged.connect(self._on_alignment_state_changed)

        self._connect_scroll_sync()
        self.sequence_viewer.selectionChanged.connect(self.consensus_row.clear_selection)

        anim = getattr(self.sequence_viewer, "_zoom_animation", None)
        if anim: anim.valueChanged.connect(self._on_zoom_changed)
        self.sequence_viewer.horizontalScrollBar().rangeChanged.connect(self._on_zoom_changed)

        from settings.theme import theme_manager
        theme_manager.themeChanged.connect(self._on_theme_changed)
        self._on_theme_changed(theme_manager.current)

        # Initial consensus visibility sync
        self._sync_consensus_visibility()

    def _sync_consensus_visibility(self):
        """Consensus spacer görünürlüğünü consensus_row ile senkronize et."""
        # consensus_row kendi visibility'sini _update_visibility ile yönetir.
        # isHidden() widget'ın kendi hide flag'ini kontrol eder (parent'tan bağımsız).
        cr_active = not self.consensus_row.isHidden() and self.consensus_row.height() > 0
        if not cr_active and self._model.is_aligned:
            self.consensus_row._update_visibility()
            cr_active = not self.consensus_row.isHidden() and self.consensus_row.height() > 0
        if cr_active:
            self.consensus_spacer.setFixedHeight(self.consensus_row.height())
            self.consensus_spacer.setVisible(True)
        else:
            self.consensus_spacer.setFixedHeight(0)
            self.consensus_spacer.setVisible(False)

    def _on_alignment_state_changed(self, is_aligned):
        self._sync_consensus_visibility()

    def _on_consensus_spacer_clicked(self):
        self._action_dialogs.on_consensus_spacer_clicked()

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if obj is self.annotation_layer and event.type() == QEvent.Resize:
            self.annotation_spacer.sync_height(self.annotation_layer.height())
        return super().eventFilter(obj, event)

    def _on_theme_changed(self, theme):
        from PyQt5.QtGui import QBrush as _B, QPalette
        from settings.color_styles import color_style_manager
        t_bg = theme.seq_bg
        for widget in (self, self.left_panel, self.splitter):
            p = widget.palette(); p.setBrush(QPalette.Window, _B(t_bg))
            widget.setAutoFillBackground(True); widget.setPalette(p)
        color_style_manager.apply_theme(theme.name)
        from settings.annotation_styles import annotation_style_manager as _asm
        _asm.apply_theme(theme.name)
        apply_scrollbar_style(self.sequence_viewer); self.update()

    def _on_annotation_changed(self, *_): self._annotation_presentation.on_annotation_changed()
    def _on_zoom_changed(self, *_): self._annotation_presentation.on_zoom_changed()
    def _on_annotation_layer_clicked(self, ann): self._action_dialogs.on_annotation_layer_clicked(ann)
    def _on_annotation_layer_double_clicked(self, ann): self._action_dialogs.on_annotation_layer_double_clicked(ann)
    def _on_ann_item_clicked(self, ann, row_index): self._action_dialogs.on_ann_item_clicked(ann, row_index)
    def _on_ann_item_double_clicked(self, ann, row_index): self._action_dialogs.on_ann_item_double_clicked(ann, row_index)

    def add_annotation(self, row_index, annotation): self._model.add_annotation(row_index, annotation)
    def remove_annotation(self, row_index, annotation_id): self._model.remove_annotation(row_index, annotation_id)
    def clear_annotations(self):
        for i in range(self._model.row_count()):
            try: self._model.clear_annotations(i)
            except: pass

    def open_find_motifs_dialog(self): self._action_dialogs.open_find_motifs_dialog()
    def open_edit_annotation_dialog(self, ann): self._action_dialogs.open_edit_annotation_dialog(ann)

    @property
    def model(self): return self._model

    def _on_header_edited(self, row_index, new_text): self._action_dialogs.on_header_edited(row_index, new_text)
    def _on_row_move_requested(self, from_index, to_index): self._action_dialogs.on_row_move_requested(from_index, to_index)
    def _on_rows_delete_requested(self, rows): self._action_dialogs.on_rows_delete_requested(rows)
    def _on_selection_changed(self, selected_rows): self._action_dialogs.on_selection_changed(selected_rows)
    def _on_row_appended(self, index, header, sequence): self._action_dialogs.on_row_appended(index, header, sequence)
    def _on_row_removed(self, index): self._action_dialogs.on_row_removed(index)
    def _on_row_moved(self, from_index, to_index): self._action_dialogs.on_row_moved(from_index, to_index)
    def _on_header_changed(self, index, new_header): self._action_dialogs.on_header_changed(index, new_header)
    def _on_model_reset(self): self._action_dialogs.on_model_reset(); self._sync_consensus_visibility()

    def add_sequence(self, header, sequence): self._model.append_row(header, sequence)
    def clear(self): self._model.clear()
    def move_row(self, from_index, to_index): self._model.move_row(from_index, to_index)
    def set_header(self, index, new_header): self._model.set_header(index, new_header)
    def selected_rows(self): return self.header_viewer._selection.selected_rows()

    def _compute_row_layout(self): return self._layout_sync.compute_row_layout()
    def _apply_layout(self, layout): self._layout_sync.apply_layout(layout)
    def _remove_all_ann_items(self): self._annotation_presentation.remove_all_ann_items()
    def _rebuild_ann_items(self, layout): self._annotation_presentation.rebuild_ann_items(layout)
    def _connect_scroll_sync(self): self._layout_sync.connect_scroll_sync()
    def _on_splitter_moved(self, pos, index): self._layout_sync.on_splitter_moved(pos, index)
    def _update_header_max_width(self): self._layout_sync.update_header_max_width()
