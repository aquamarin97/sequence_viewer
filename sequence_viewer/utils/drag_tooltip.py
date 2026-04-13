# utils/drag_tooltip.py
"""
DragTooltip — selection info overlay (bp + Tm).

FloatingPanel'in ince sarmalayıcısı. Viewport çocuk widget'ı olarak çalışır.
"""
from __future__ import annotations

from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QWidget

from .floating_panel import FloatingPanel
from .sequence_utils import format_tm


class DragTooltip(FloatingPanel):
    """
    Seçim sırasında ve seçim aktifken gösterilen bp / Tm bilgi paneli.

    Tek satır format:  "156 bp  62.3 °C"  (Tm varsa)
                       "156 bp"            (Tm yoksa)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    # ── Public API ────────────────────────────────────────────────────────────

    def show_bp_tm(self, anchor: QPoint, bp: int, tm: float | None) -> None:
        """Bp ve Tm'yi (varsa) tek satırda göster. anchor = viewport koordinatı."""
        text = f"{bp} bp  {format_tm(tm)}" if tm is not None else f"{bp} bp"
        self.update_content([("", text)])
        self.show_at(anchor)

    def show_bp_only(self, anchor: QPoint, bp: int) -> None:
        """Yalnızca Bp'yi göster (çok satırlı seçim). anchor = viewport koordinatı."""
        self.update_content([("", f"{bp} bp")])
        self.show_at(anchor)

    def clear_tooltip(self) -> None:
        """clear_panel için alias — controller call-site'larında okunabilirlik."""
        self.clear_panel()
