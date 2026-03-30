# model/alignment_metadata.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

@dataclass
class AlignmentMetadata:
    algorithm:  str                  = "unknown"
    parameters: Dict[str, Any]       = field(default_factory=dict)
    aligned_at: Optional[datetime]   = field(default=None)
    source:     str                  = ""

    def __post_init__(self):
        if self.aligned_at is None:
            self.aligned_at = datetime.now(tz=timezone.utc)

    def summary(self) -> str:
        ts = self.aligned_at.strftime("%Y-%m-%d %H:%M UTC") if self.aligned_at else "unknown time"
        params_str = ", ".join(f"{k}={v}" for k, v in self.parameters.items()) if self.parameters else "default parameters"
        return f"{self.algorithm} ({params_str}) — {ts}"
