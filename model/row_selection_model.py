# model/row_selection_model.py
"""
Windows Gezgini tarzı çoklu satır seçim modeli.

Desteklenen etkileşimler
------------------------
click(row)              Tek satır seç, önceki seçimi temizle. Anchor = row.
ctrl_click(row)         Satırı toggle et. Anchor = row.
shift_click(row)        Anchor'dan row'a kadar aralığı seç.
                        Önceki Ctrl seçimleri temizlenir (klasik Windows davranışı).
select_all(count)       Tüm satırları seç.
clear()                 Seçimi tamamen temizle.

Değişiklik bildirimi
--------------------
Her handle_* metodu değişen satır indekslerinin kümesini döner.
View sadece bu satırları yeniden çizerek gereksiz tam-repaint'ten kaçınabilir.
(Şimdilik tüm viewport güncelleniyor ama API ileride optimize edilebilir.)
"""

from __future__ import annotations

from typing import FrozenSet, Optional, Set


class RowSelectionModel:
    """
    Seçim durumu ve Windows mantığı.
    PyQt'ye bağımlı değil — saf Python.
    """

    def __init__(self) -> None:
        self._selected: Set[int] = set()
        self._anchor:   Optional[int] = None   # Shift-click için referans satır

    # ------------------------------------------------------------------
    # Sorgulama
    # ------------------------------------------------------------------

    def is_selected(self, row: int) -> bool:
        return row in self._selected

    def selected_rows(self) -> FrozenSet[int]:
        """Seçili satır indekslerinin değiştirilemez kopyasını döner."""
        return frozenset(self._selected)

    def count(self) -> int:
        return len(self._selected)

    def is_empty(self) -> bool:
        return not self._selected

    @property
    def anchor(self) -> Optional[int]:
        return self._anchor

    # ------------------------------------------------------------------
    # Etkileşim yöneticileri
    # ------------------------------------------------------------------

    def handle_click(self, row: int, row_count: int) -> FrozenSet[int]:
        """
        Sade tıklama: tek satırı seç, geri kalanı temizle.
        Anchor yeni seçili satıra taşınır.
        """
        changed = self._selected.symmetric_difference({row})
        self._selected = {row}
        self._anchor   = row
        return frozenset(changed | {row})

    def handle_ctrl_click(self, row: int, row_count: int) -> FrozenSet[int]:
        """
        Ctrl+tıklama: satırı toggle et.
        Anchor her zaman bu satıra taşınır.
        """
        if row in self._selected:
            self._selected.discard(row)
        else:
            self._selected.add(row)
        self._anchor = row
        return frozenset({row})

    def handle_shift_click(self, row: int, row_count: int) -> FrozenSet[int]:
        """
        Shift+tıklama: anchor'dan row'a kadar aralığı seç.
        Anchor değişmez.
        """
        anchor = self._anchor if self._anchor is not None else row
        lo = min(anchor, row)
        hi = max(anchor, row)

        old       = frozenset(self._selected)
        new_range = set(range(lo, hi + 1))

        # Windows: Shift+Click önceki Ctrl seçimlerini temizler,
        # sadece yeni aralık aktif olur.
        self._selected = new_range

        changed = old.symmetric_difference(new_range)
        return frozenset(changed)

    def select_all(self, row_count: int) -> FrozenSet[int]:
        """Ctrl+A: tüm satırları seç."""
        old          = frozenset(self._selected)
        self._selected = set(range(row_count))
        self._anchor   = 0 if row_count > 0 else None
        return frozenset(self._selected.symmetric_difference(old))

    def clear(self) -> FrozenSet[int]:
        """Escape: seçimi temizle."""
        changed        = frozenset(self._selected)
        self._selected = set()
        self._anchor   = None
        return changed

    def remove_row(self, removed_index: int) -> None:
        """
        Bir satır silindiğinde seçim indekslerini kaydır.
        Workspace, model.rowRemoved sinyali geldiğinde bu metodu çağırmalıdır.
        """
        new_selected: Set[int] = set()
        for r in self._selected:
            if r < removed_index:
                new_selected.add(r)
            elif r > removed_index:
                new_selected.add(r - 1)
            # r == removed_index → seçimden çıkarılıyor

        self._selected = new_selected

        if self._anchor is not None:
            if self._anchor == removed_index:
                self._anchor = None
            elif self._anchor > removed_index:
                self._anchor -= 1

    def move_row(self, from_index: int, to_index: int) -> None:
        """
        Satır taşındığında seçim indekslerini senkronize et.
        Workspace, model.rowMoved sinyali geldiğinde çağırmalıdır.
        """
        # Taşınan satır seçiliydi mi?
        was_selected = from_index in self._selected

        # from_index'i geçici olarak çıkar, diğerlerini kaydır
        new_selected: Set[int] = set()
        for r in self._selected:
            if r == from_index:
                continue
            shifted = _shift_for_move(r, from_index, to_index)
            new_selected.add(shifted)

        if was_selected:
            new_selected.add(to_index)

        self._selected = new_selected

        if self._anchor is not None:
            if self._anchor == from_index:
                self._anchor = to_index
            else:
                self._anchor = _shift_for_move(self._anchor, from_index, to_index)


def _shift_for_move(row: int, from_idx: int, to_idx: int) -> int:
    """
    from_idx → to_idx taşımasında 'row' indeksinin yeni değerini hesaplar.
    'row' taşınan satırın kendisi DEĞİLDİR.
    """
    if from_idx < to_idx:
        # Aşağıya taşındı: [from_idx+1 .. to_idx] aralığı bir yukarı kayar
        if from_idx < row <= to_idx:
            return row - 1
    else:
        # Yukarıya taşındı: [to_idx .. from_idx-1] aralığı bir aşağı kayar
        if to_idx <= row < from_idx:
            return row + 1
    return row