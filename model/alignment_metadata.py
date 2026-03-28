# model/alignment_metadata.py
"""
Hizalama işleminin provenance bilgisi.

Sorumluluklar
-------------
* Hangi algoritmanın, hangi parametrelerle, ne zaman çalıştırıldığını tutmak.
* AlignmentDataModel.is_aligned = True olduğunda anlam kazanır.
* Persistence katmanı bu objeyi dosyaya yazar; domain bu objeyi sadece taşır.

Tasarım notu
------------
Qt bağımlılığı yok. Saf Python dataclass — test edilmesi ve
persistence katmanından bağımsız olarak kullanılması kolaydır.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class AlignmentMetadata:
    """
    MSA provenance kaydı.

    Parametreler
    ------------
    algorithm  : Kullanılan araç adı ("MUSCLE", "MAFFT", "Clustal", "manual", …).
    parameters : Algoritmanın çalıştırıldığı parametre sözlüğü.
                 Örn: {"maxiters": 16, "gap_open": -2.0}
    aligned_at : Hizalama tarihi (UTC). Verilmezse şu an atanır.
    source     : İsteğe bağlı kaynak açıklaması ("imported from .aln", vb.).
    """

    algorithm:  str                  = "unknown"
    parameters: Dict[str, Any]       = field(default_factory=dict)
    aligned_at: Optional[datetime]   = field(default=None)
    source:     str                  = ""

    def __post_init__(self) -> None:
        # aligned_at verilmemişse şu anki UTC zamanını ata
        if self.aligned_at is None:
            self.aligned_at = datetime.now(tz=timezone.utc)

    # ------------------------------------------------------------------
    # Gösterim yardımcısı
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """İnsan okunabilir tek satır özet."""
        ts = (
            self.aligned_at.strftime("%Y-%m-%d %H:%M UTC")
            if self.aligned_at
            else "unknown time"
        )
        params_str = (
            ", ".join(f"{k}={v}" for k, v in self.parameters.items())
            if self.parameters
            else "default parameters"
        )
        return f"{self.algorithm} ({params_str}) — {ts}"