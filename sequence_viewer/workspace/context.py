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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QSplitter, QWidget

    from sequence_viewer.features.annotation_layer.annotation_layer_widget import (
        AnnotationLayerWidget,
    )
    from sequence_viewer.features.consensus_row.consensus_row_widget import ConsensusRowWidget
    from sequence_viewer.features.header_viewer.header_spacer_widgets import (
        AnnotationSpacerWidget,
        ConsensusSpacerWidget,
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
        self.model: AlignmentDataModel = None  # type: ignore[assignment]
        self.undo_stack: UndoStack = None  # type: ignore[assignment]

        # ── UI widget'ları (WorkspaceLayoutManager.setup_ui tarafından doldurulur) ──
        self.sequence_viewer: SequenceViewerWidget = None  # type: ignore[assignment]
        self.header_viewer: HeaderViewerWidget = None  # type: ignore[assignment]
        self.annotation_layer: AnnotationLayerWidget = None  # type: ignore[assignment]
        self.consensus_row: ConsensusRowWidget = None  # type: ignore[assignment]
        self.consensus_spacer: ConsensusSpacerWidget = None  # type: ignore[assignment]
        self.annotation_spacer: AnnotationSpacerWidget = None  # type: ignore[assignment]
        self.splitter: QSplitter = None  # type: ignore[assignment]
        self.left_panel: QWidget = None  # type: ignore[assignment]
        self.ruler: RulerWidget = None  # type: ignore[assignment]
        self.pos_ruler: SequencePositionRulerWidget = None  # type: ignore[assignment]

        # ── Coordinator'lar & controller'lar (workspace.__init__ tarafından doldurulur) ──
        self.layout_sync: WorkspaceLayoutScrollSync = None  # type: ignore[assignment]
        self.annotation_presentation: WorkspaceAnnotationPresentation = None  # type: ignore[assignment]
        self.action_dialogs: WorkspaceActionDialogCoordinator = None  # type: ignore[assignment]
        self.clipboard_controller: WorkspaceClipboardController = None  # type: ignore[assignment]
        self.command_controller: WorkspaceCommandController = None  # type: ignore[assignment]
        self.keyboard_controller: WorkspaceKeyboardController = None  # type: ignore[assignment]
        self.style_applier: WorkspaceStyleApplier = None  # type: ignore[assignment]
