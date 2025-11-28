# msa_viewer/sequence_viewer/sequence_viewer_model.py

from typing import List, Optional, Tuple


class SequenceViewerModel:
    """
    SequenceViewer'ın CMV mimarisindeki Model katmanı.

    Sorumluluklar:
    - Sekans verisini tutmak (saf string listesi)
    - En uzun sekans uzunluğunu (max_sequence_length) cache'lemek
    - Seçim (selection) durumunu yönetmek:
        * selection_start_row / selection_start_col
        * current_selection_cols (sadece sütun aralığı; ruler için yeterli)
    - Satır / sütun indeks clamp işlemleri
    - Seçim güncellendiğinde hangi satır/sütun aralığının highlight edileceğini hesaplamak
      (view bu aralığı kullanarak highlight yapacak)
    """

    def __init__(self) -> None:
        # Sekans string'leri (her satır bir sekans)
        self._sequences: List[str] = []

        # En uzun sekans uzunluğu (ruler ve zoom hesapları için cache)
        self.max_sequence_length: int = 0

        # Seçim başlangıç noktası (satır/sütun) – drag sırasında kullanılır
        self.selection_start_row: Optional[int] = None
        self.selection_start_col: Optional[int] = None

        # Şu anki seçim sütun aralığı (start, end) inclusive
        # Ruler pivot hesapları için tutulur.
        self.current_selection_cols: Optional[Tuple[int, int]] = None

    # ------------------------------------------------------------------
    # Sekans yönetimi
    # ------------------------------------------------------------------

    def add_sequence(self, sequence: str) -> int:
        """
        Yeni bir sekans ekler, max_sequence_length'i günceller
        ve eklenen sekansın satır indeksini döner.
        """
        self._sequences.append(sequence)
        seq_len = len(sequence)
        if seq_len > self.max_sequence_length:
            self.max_sequence_length = seq_len
        return len(self._sequences) - 1

    def clear_sequences(self) -> None:
        """
        Tüm sekansları ve seçim durumunu temizler.
        """
        self._sequences.clear()
        self.max_sequence_length = 0
        self.clear_selection()

    def recalc_max_sequence_length(self) -> int:
        """
        Sekanslar değişmişse (dışarıdan modifiye edildiğinde) en uzun uzunluğu yeniden hesaplar.
        """
        self.max_sequence_length = max((len(s) for s in self._sequences), default=0)
        return self.max_sequence_length

    def get_sequences(self) -> List[str]:
        """
        Tüm sekansların bir kopyasını döner.
        """
        return list(self._sequences)

    def get_row_count(self) -> int:
        """
        Toplam sekans (satır) sayısı.
        """
        return len(self._sequences)

    def get_sequence(self, row_index: int) -> str:
        """
        Verilen satır indeksindeki sekansı döner.
        IndexError throw etmesini normal kabul ediyoruz.
        """
        return self._sequences[row_index]

    # ------------------------------------------------------------------
    # Seçim yönetimi
    # ------------------------------------------------------------------

    def clear_selection(self) -> None:
        """
        Seçimi tamamen temizler.
        """
        self.selection_start_row = None
        self.selection_start_col = None
        self.current_selection_cols = None

    def start_selection(self, row: int, col: int) -> bool:
        """
        Yeni bir seçim başlatır (mouse press anı).
        Sadece satır range'ine ve col >= 0 şartına bakar; sütun clamp'i update sırasında yapılır.
        Geçerli bir başlangıç ise True, aksi halde False döner.
        """
        row_count = self.get_row_count()
        if row_count == 0:
            self.clear_selection()
            return False

        if row < 0 or row >= row_count or col < 0:
            # Geçersiz başlangıç → mevcut seçimi temizle
            self.clear_selection()
            return False

        self.selection_start_row = row
        self.selection_start_col = col
        # İlk anda "tek hücre"lik seçim gibi davranacağız; ayrıntı update_selection'da hesaplanır.
        return True

    def update_selection(
        self,
        current_row: int,
        current_col: int,
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Drag sırasında mevcut mouse pozisyonuna göre seçim aralığını günceller.

        Dönen değer:
            (row_start, row_end, col_start, col_end)  veya geçerli bir seçim yoksa None

        Bu aralık view tarafından highlight için kullanılacak:
            view.set_visual_selection(row_start, row_end, col_start, col_end)
        """
        if self.selection_start_row is None or self.selection_start_col is None:
            return None

        clamped_start_col = self._clamp_column_index(self.selection_start_col)
        clamped_current_col = self._clamp_column_index(current_col)
        if clamped_start_col is None or clamped_current_col is None:
            # Sekans yok veya max_sequence_length 0 → seçim sıfırlanır
            self.clear_selection()
            return None

        row_count = self.get_row_count()
        if row_count == 0:
            self.clear_selection()
            return None

        # Satır aralığını clamp et
        row_start = max(0, min(self.selection_start_row, current_row))
        row_end = min(row_count - 1, max(self.selection_start_row, current_row))

        # Sütun aralığı
        col_start = min(clamped_start_col, clamped_current_col)
        col_end = max(clamped_start_col, clamped_current_col)

        # Sadece sütun aralığını state olarak saklıyoruz (ruler için yeterli)
        if col_start >= 0 and col_end >= 0:
            self.current_selection_cols = (col_start, col_end)
        else:
            self.current_selection_cols = None

        return row_start, row_end, col_start, col_end

    def get_selection_column_range(self) -> Optional[Tuple[int, int]]:
        """
        Şu anki seçim sütun aralığını döner (start, end) inclusive.
        Seçim yoksa None.
        """
        return self.current_selection_cols

    def get_selection_center_nt(self) -> Optional[float]:
        """
        Seçimin nt merkezini döner.
        Zoom pivotu için kullanışlıdır.
        """
        if self.current_selection_cols is None or self.max_sequence_length <= 0:
            return None

        s, e = self.current_selection_cols
        if s > e:
            s, e = e, s

        # Orijinal koddaki gibi (s + e + 1) / 2.0
        center_nt = (s + e + 1) / 2.0
        # Güvenlik için nt aralığına clamp
        center_nt = max(0.0, min(center_nt, float(self.max_sequence_length)))
        return center_nt

    # ------------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------------

    def _clamp_column_index(self, col: int) -> Optional[int]:
        """
        Kolon indeksini [0, max_sequence_length - 1] aralığına clamp eder.
        max_sequence_length <= 0 ise None döner.
        """
        if self.max_sequence_length <= 0:
            return None
        return max(0, min(col, self.max_sequence_length - 1))
