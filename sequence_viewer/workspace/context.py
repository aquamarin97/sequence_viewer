# sequence_viewer/workspace/context.py
"""
WorkspaceContext — coordinator'ların workspace widget'ı yerine tuttuğu
dependency container.

Sorun: Her coordinator daha önce `self.workspace` (SequenceWorkspaceWidget)
tutuyordu ve ondan her şeye ulaşıyordu (God Object anti-pattern). Bu yüzden
workspace.py 15+ backward-compatible alias barındırmak zorundaydı.

Çözüm: Coordinator'lar artık WorkspaceContext alır; sadece ihtiyaç duydukları
bileşenlere isimli attribute üzerinden erişirler. workspace.py ince bir facade
olarak kalır.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QSplitter, QWidget

    from sequence_viewer.features.annotation_layer.annotation_layer_widget import (
        AnnotationLayerWidget,
    )
    from sequence_viewer.features.consensus_row.consensus_row_widget import ConsensusRowWidget
    from sequence_viewer.features.consensus_row.consensus_spacer_widget import (
        ConsensusSpacerWidget,
    )
    from sequence_viewer.features.header_viewer.header_spacer_widgets import (
        AnnotationSpacerWidget,
    )
    from sequence_viewer.features.header_viewer.header_viewer_widget import HeaderViewerWidget
    from sequence_viewer.features.navigation_ruler.navigation_ruler_widget import RulerWidget
    from sequence_viewer.features.position_ruler.position_ruler_widget import (
        SequencePositionRulerWidget,
    )
    from sequence_viewer.features.sequence_viewer.sequence_viewer_widget import SequenceViewerWidget
    from sequence_viewer.model.alignment_data_model import AlignmentDataModel
    from sequence_viewer.model.undo_stack import UndoStack
    from sequence_viewer.workspace.controllers.clipboard_controller import (
        WorkspaceClipboardController,
    )
    from sequence_viewer.workspace.controllers.command_controller import WorkspaceCommandController
    from sequence_viewer.workspace.controllers.keyboard_controller import (
        WorkspaceKeyboardController,
    )
    from sequence_viewer.workspace.coordinators.action_dialog import (
        WorkspaceActionDialogCoordinator,
    )
    from sequence_viewer.workspace.coordinators.annotation_presentation import (
        WorkspaceAnnotationPresentation,
    )
    from sequence_viewer.workspace.coordinators.layout_scroll_sync import WorkspaceLayoutScrollSync
    from sequence_viewer.workspace.coordinators.selection.annotation_selection_coordinator import (
        WorkspaceAnnotationSelectionCoordinator,
    )
    from sequence_viewer.workspace.coordinators.selection.row_selection_coordinator import (
        WorkspaceRowSelectionCoordinator,
    )
    from sequence_viewer.workspace.coordinators.selection.selection_state import (
        WorkspaceSelectionState,
    )
    from sequence_viewer.workspace.styling.style_applier import WorkspaceStyleApplier


class WorkspaceContext:
    """Tüm workspace alt bileşenlerinin yaşam süresi boyunca tutulduğu kap.

    SequenceWorkspaceWidget.__init__ sırasında iki aşamada doldurulur:
      1. UI widget'ları  → WorkspaceLayoutManager.setup_ui(ctx) tarafından
      2. Coordinator'lar → workspace.__init__ içinde sırayla atanır

    Coordinator'lar arasındaki döngüsel bağımlılıkları engellemek için
    context mutable bir nesne olarak tutulur; her bileşen inşa edildikten
    hemen sonra ilgili attribute set edilir.
    """

    def __init__(self, root_widget: "QWidget") -> None:
        # SequenceWorkspaceWidget'ın kendisi — dialog parent'ı, focus, vb. için
        self.root_widget: QWidget = root_widget

        # ── Model katmanı ────────────────────────────────────────────────
        self.model: Optional[AlignmentDataModel] = None
        self.undo_stack: Optional[UndoStack] = None

        # ── UI widget'ları (WorkspaceLayoutManager.setup_ui tarafından doldurulur) ──
        self.sequence_viewer: Optional[SequenceViewerWidget] = None
        self.header_viewer: Optional[HeaderViewerWidget] = None
        self.annotation_layer: Optional[AnnotationLayerWidget] = None
        self.consensus_row: Optional[ConsensusRowWidget] = None
        self.consensus_spacer: Optional[ConsensusSpacerWidget] = None
        self.annotation_spacer: Optional[AnnotationSpacerWidget] = None
        self.splitter: Optional[QSplitter] = None
        self.left_panel: Optional[QWidget] = None
        self.ruler: Optional[RulerWidget] = None
        self.pos_ruler: Optional[SequencePositionRulerWidget] = None

        # ── Coordinator'lar & controller'lar (workspace.__init__ tarafından doldurulur) ──
        self.layout_sync: Optional[WorkspaceLayoutScrollSync] = None
        self.annotation_presentation: Optional[WorkspaceAnnotationPresentation] = None
        self.action_dialogs: Optional[WorkspaceActionDialogCoordinator] = None
        self.selection_state: Optional[WorkspaceSelectionState] = None
        self.annotation_selection: Optional[WorkspaceAnnotationSelectionCoordinator] = None
        self.row_selection: Optional[WorkspaceRowSelectionCoordinator] = None
        self.clipboard_controller: Optional[WorkspaceClipboardController] = None
        self.command_controller: Optional[WorkspaceCommandController] = None
        self.keyboard_controller: Optional[WorkspaceKeyboardController] = None
        self.style_applier: Optional[WorkspaceStyleApplier] = None
