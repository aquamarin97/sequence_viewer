# features/annotation_layer/annotation_layout_engine.py
"""
Greedy lane (şerit) atama motoru.

Algoritma
---------
1. Annotasyonları start pozisyonuna göre sırala.
2. Her annotasyon için mevcut lane'leri sırayla kontrol et:
   o lane'deki son annotasyon ile örtüşüyor mu?
   → Hayır: bu lane'e yerleştir.
   → Evet: bir sonraki lane'i dene.
3. Uygun lane bulunamazsa yeni lane aç.

Sonuç: {annotation_id: lane_index (0-based)}
"""

from __future__ import annotations

from typing import Dict, List

from model.annotation import Annotation


def assign_lanes(annotations: List[Annotation]) -> Dict[str, int]:
    """
    Annotasyon listesini lane'lere atar.
    Dönen dict: {annotation.id: lane_index}
    """
    if not annotations:
        return {}

    # Start'a göre sırala; eşitlikte uzunu öne al (daha iyi dolgu)
    sorted_anns = sorted(annotations, key=lambda a: (a.start, -a.length()))

    # lane_end[i] = i. lane'deki son annotasyonun end pozisyonu
    lane_ends: List[int] = []
    result:    Dict[str, int] = {}

    for ann in sorted_anns:
        placed = False
        for lane_idx, last_end in enumerate(lane_ends):
            # 1 bp boşluk bırak — bitişik annotasyonlar aynı lane'de olabilsin
            if ann.start > last_end + 1:
                lane_ends[lane_idx] = ann.end
                result[ann.id]      = lane_idx
                placed = True
                break

        if not placed:
            # Yeni lane aç
            result[ann.id] = len(lane_ends)
            lane_ends.append(ann.end)

    return result


def lane_count(lane_assignment: Dict[str, int]) -> int:
    """Toplam lane sayısını döner."""
    if not lane_assignment:
        return 0
    return max(lane_assignment.values()) + 1