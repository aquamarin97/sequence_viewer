# utils/sequence_utils.py
"""
Sequence analysis utility functions.

Requires: biopython  (pip install biopython)
"""
from __future__ import annotations

from typing import Optional

from Bio.Seq import Seq
from Bio.SeqUtils import MeltingTemp as mt

from sequence_viewer.utils.tm_settings_manager import tm_settings_manager


# ---------------------------------------------------------------------------
# Base pair count
# ---------------------------------------------------------------------------

def selection_bp(col_start: int, col_end: int) -> int:
    """
    Seçimin kapsadığı hizalama kolonu sayısını döndürür (her iki uç dahil).
    """
    return max(0, col_end - col_start + 1)


# ---------------------------------------------------------------------------
# Melting temperature (Tm)
# ---------------------------------------------------------------------------

def calculate_tm(sequence: str) -> Optional[float]:
    """
    DNA/RNA dizisi için erime sıcaklığını (Tm, °C) hesaplar.

    Yöntem ve parametreler tm_settings_manager üzerinden okunur:
      "NN"      -> Tm_NN  — Nearest-Neighbor (SantaLucia 1998, önerilen)
      "GC"      -> Tm_GC  — GC-içerik tabanlı empirik formül
      "Wallace" -> Tm_Wallace — klasik kısa-oligo kural-parmak formülü

    Geçersiz veya boş dizi için None döner.
    """
    if not sequence:
        return None

    try:
        seq = Seq(sequence)
        method = tm_settings_manager.method.upper()

        if method == "WALLACE":
            return float(mt.Tm_Wallace(seq))

        if method == "GC":
            return float(mt.Tm_GC(seq, **tm_settings_manager.gc_params()))

        # Default: NN
        return float(mt.Tm_NN(seq, nn_table=mt.DNA_NN3, **tm_settings_manager.nn_params()))

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_tm(tm: Optional[float]) -> str:
    """'62.3 °C' gibi biçimlendirilmiş Tm string'i döndürür; None için '—'."""
    if tm is None:
        return "\u2014"
    return f"{tm:.1f} \u00b0C"
