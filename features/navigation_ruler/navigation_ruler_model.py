# msa_viewer/navigation_ruler/navigation_ruler_model.py

from dataclasses import dataclass
from typing import List, Sequence, Optional
import math


@dataclass
class NavigationTickLayout:
    """
    Navigation cetveli için hesaplanmış tick/layout bilgisi.
    QPainter tarafı bu veriyi kullanarak çizim yapar.
    """
    max_len: int
    tick_step: int
    major_ticks: List[int]   # nt pozisyonları (0-based)
    minor_ticks: List[int]   # nt pozisyonları (0-based)


class NavigationRulerModel:
    """
    Navigation ruler (minimap) için Model katmanı.

    Sorumluluklar:
    - En uzun dizi uzunluğunu cache'lemek:
        * _cached_max_len
        * _last_seq_count
    - max_len ve pixel genişliğine göre:
        * "nice" tick step seçmek
        * major/minor tick nt pozisyonlarını üretmek
    - max_len'e bağlı label formatlama
    - x (piksel) -> nt dönüşümü
    """

    def __init__(self) -> None:
        self._cached_max_len: int = 0
        self._last_seq_count: int = 0

    # --------------------------------------------------------------
    # max_len cache
    # --------------------------------------------------------------

    @property
    def cached_max_len(self) -> int:
        return self._cached_max_len

    def recompute_max_len_if_needed(self, sequence_items: Sequence) -> int:
        """
        viewer.sequence_items içinden en uzun sekans uzunluğunu hesaplar.
        Sadece satır sayısı veya max_len değiştiyse cache'i günceller.
        """
        seq_count = len(sequence_items)
        new_max_len = max(
            (len(getattr(it, "sequence", "")) for it in sequence_items),
            default=0,
        )

        if seq_count != self._last_seq_count or new_max_len != self._cached_max_len:
            self._last_seq_count = seq_count
            self._cached_max_len = new_max_len

        return self._cached_max_len

    # --------------------------------------------------------------
    # Tick / layout hesaplama
    # --------------------------------------------------------------

    def compute_tick_layout(
        self,
        pixel_width: int,
        target_px: int = 60,
    ) -> Optional[NavigationTickLayout]:
        """
        Şu anki cached_max_len ve verilen pixel genişliğine göre
        major/minor tick layout'unu hesaplar.
        """
        max_nt = self._cached_max_len
        if max_nt <= 0 or pixel_width <= 0:
            return None

        step = self._nice_tick_step(max_nt, pixel_width, target_px)

        # Minor tickler
        minor_step = max(step // 5, 1)
        minor_ticks: List[int] = []
        nt = 0
        while nt <= max_nt:
            minor_ticks.append(nt)
            nt += minor_step

        # Major tickler
        major_ticks: List[int] = []
        nt = 0
        while nt <= max_nt:
            major_ticks.append(nt)
            nt += step

        if major_ticks:
            last_nt = major_ticks[-1]
            delta = max_nt - last_nt
            if delta != 0:
                if delta < step * 0.5:
                    major_ticks[-1] = max_nt
                else:
                    major_ticks.append(max_nt)

        return NavigationTickLayout(
            max_len=max_nt,
            tick_step=step,
            major_ticks=major_ticks,
            minor_ticks=minor_ticks,
        )

    # --------------------------------------------------------------
    # Label formatlama + x→nt mapping
    # --------------------------------------------------------------

    def format_label(self, value: int) -> str:
        """
        Cetvel üzerindeki sayıları yazarken kullanılacak format.
        - max_len <= 1_000_000: normal sayı (örn. 5050)
        - max_len  > 1_000_000: K'li gösterim (örn. 10K, 250K)
        İlk label 1 ise her zaman '1' yazılır.
        """
        max_len = self._cached_max_len

        if value == 1:
            return "1"

        if max_len > 1_000_000:
            k_val = int(round(value / 1000.0))
            return f"{k_val}K"

        return str(value)

    def x_to_nt(self, x: int, pixel_width: int) -> float:
        """
        Cetvel üzerindeki piksel konumunu nt indeksine dönüştür.
        """
        max_len = self._cached_max_len
        if max_len <= 0 or pixel_width <= 0:
            return 0.0

        ratio = min(max(x / float(pixel_width), 0.0), 1.0)
        return ratio * max_len

    # --------------------------------------------------------------
    # Nice tick step seçimi (eski _nice_tick_step)
    # --------------------------------------------------------------

    @staticmethod
    def _nice_tick_step(
        max_nt: int,
        pixel_width: int,
        target_px: int = 60,
    ) -> int:
        """
        Ölçeklenen cetvel için "güzel" (1,2,5 x 10^k) aralıklı tick step seçer.
        """
        if max_nt <= 0 or pixel_width <= 0:
            return max_nt if max_nt > 0 else 1

        raw_step = (max_nt * target_px) / float(pixel_width)
        if raw_step <= 0:
            return 1

        power = 10 ** int(math.floor(math.log10(raw_step)))
        base = raw_step / power

        if base <= 1:
            nice = 1
        elif base <= 2:
            nice = 2
        elif base <= 5:
            nice = 5
        else:
            nice = 10

        return int(nice * power)
