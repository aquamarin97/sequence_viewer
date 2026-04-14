# sequence_viewer/workspace/controllers/state_cleaner.py
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sequence_viewer.workspace.context import WorkspaceContext


class WorkspaceStateCleaner:
    """Tüm UI etkileşim state'ini temizleyen koordinatör.

    Her widget kendi state'ini `clear_interaction_state()` metoduyla
    yönetir; bu sınıf yalnızca hangi bileşenin temizleneceğini
    belirler — private attribute'a hiç dokunmaz.
    """

    def __init__(self, ctx: "WorkspaceContext") -> None:
        self._ctx = ctx

    # ── Public API ────────────────────────────────────────────────────────

    def clear_all_interaction_state(self) -> None:
        """Undo geri yükleme sonrasında tüm etkileşim state'ini sıfırlar."""
        ctx = self._ctx
        ctx.action_dialogs.clear_selected_annotations()
        ctx.annotation_presentation.clear_annotation_selection()
        ctx.annotation_layer.clear_annotation_selection()
        ctx.sequence_viewer.clear_interaction_state()
        ctx.header_viewer.clear_interaction_state()
        ctx.consensus_spacer.set_selected(False)
        ctx.consensus_row.clear_selection()

    def clear_annotation_delete_state(self) -> None:
        """Annotation silme mutation'ı sırasında ilgili state'i temizler."""
        ctx = self._ctx
        ctx.action_dialogs.clear_selected_annotations()
        ctx.annotation_presentation.clear_annotation_selection()
        ctx.annotation_layer.clear_annotation_selection()
        ctx.sequence_viewer.clear_interaction_state()

    def clear_consensus_delete_state(self) -> None:
        """Consensus annotation silme mutation'ı sırasında ilgili state'i temizler."""
        ctx = self._ctx
        ctx.consensus_row.clear_selection()   # _selected_ann_ids, _selection_ranges, _is_selected, spacer bildirimi
        ctx.consensus_spacer.set_selected(False)  # parent walk'a güvenmemek için açık çağrı
        ctx.sequence_viewer.clear_interaction_state()
