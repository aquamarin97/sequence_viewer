# msa_viewer/header_viewer/header_viewer_model.py

from typing import List


class HeaderViewerModel:
    """
    Header viewer için Model katmanı.

    Şimdilik sadece header metinlerini (ham string) tutuyor.
    İleride her satır için ek metadata (renk, grup, filtre flag'i, vb.)
    eklenecekse buraya koyabiliriz.
    """

    def __init__(self) -> None:
        # Sırasıyla header metinleri (ham, numarasız)
        self._headers: List[str] = []

    # ------------------------------------------------------------------
    # Header listesi yönetimi
    # ------------------------------------------------------------------

    def add_header(self, text: str) -> int:
        """
        Yeni bir header ekler ve satır indeksini döner.
        """
        self._headers.append(text)
        return len(self._headers) - 1

    def clear_headers(self) -> None:
        """
        Tüm header'ları temizler.
        """
        self._headers.clear()

    def get_headers(self) -> List[str]:
        """
        Header string'lerinin bir kopyasını döner.
        """
        return list(self._headers)

    def get_row_count(self) -> int:
        """
        Toplam header satır sayısı.
        """
        return len(self._headers)

    def get_header(self, index: int) -> str:
        """
        Verilen satır indeksindeki header metnini döner.
        IndexError fırlatması normal kabul edilir.
        """
        return self._headers[index]
