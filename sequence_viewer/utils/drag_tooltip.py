# utils/drag_tooltip.py
"""
DragTooltip — floating panel specialised for drag-selection feedback.

Thin wrapper around FloatingPanel that formats Bp / Tm rows and
exposes the simplified show_at / clear_tooltip API used by the
controller and the consensus row widget.
"""
from __future__ import annotations

from PyQt5.QtCore import QPoint

from .floating_panel import FloatingPanel
from .sequence_utils import format_tm


class DragTooltip(FloatingPanel):
    """
    Floating info panel shown while the user drags to select a region.

    Single-row selection  →  Bp + Tm rows
    Multi-row selection   →  Bp row only
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def show_bp_tm(self, global_pos: QPoint, bp: int, tm: float | None) -> None:
        """Show Bp and Tm for a single-row selection."""
        self.update_content([
            ("Bp", str(bp)),
            ("Tm", format_tm(tm)),
        ])
        self.show_at(global_pos)

    def show_bp_only(self, global_pos: QPoint, bp: int) -> None:
        """Show Bp only for a multi-row selection."""
        self.update_content([("Bp", str(bp))])
        self.show_at(global_pos)

    def clear_tooltip(self) -> None:
        """Alias for clear_panel — keeps controller/widget call-sites readable."""
        self.clear_panel()
