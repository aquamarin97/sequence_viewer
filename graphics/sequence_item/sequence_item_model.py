# graphics/sequence_item_model.py

from typing import Optional, Tuple, Dict

from PyQt5.QtGui import QColor
from graphics.sequence_item.sequence_glyph_cache import default_nucleotide_color_map



class SequenceItemModel:
    """
    Tek bir sekans satırının model katmanı.

    Sorumluluklar:
    - sequence / sequence_upper / length
    - char_width / char_height
    - zoom'a bağlı:
        * current_font_size
        * display_mode (TEXT / BOX / LINE)
        * box_height / line_height
    - selection_range (start, end)  [end exclusive]
    - LOD override: _lod_max_mode
    """

    TEXT_MODE = "text"
    BOX_MODE = "box"
    LINE_MODE = "line"

    _TEXT_BOX_THRESHOLD = 8.0
    _BOX_LINE_THRESHOLD = 5.0

    def __init__(
        self,
        sequence: str,
        char_width: float = 12.0,
        char_height: float = 18.0,
        color_map: Optional[Dict[str, QColor]] = None,
    ) -> None:
        self.sequence: str = sequence
        self.sequence_upper: str = sequence.upper()
        self.length: int = len(sequence)

        self.char_width: float = max(char_width, 0.001)
        self.char_height: int = max(1, int(round(char_height)))

        self.color_map: Dict[str, QColor] = color_map or default_nucleotide_color_map()

        self.default_char_width: float = self.char_width

        # Seçim (start, end) [end exclusive]
        self.selection_range: Optional[Tuple[int, int]] = None

        # Zoom / font / mod state
        self.base_font_size: float = self.char_height * 0.6
        self.display_mode: str = self.TEXT_MODE
        self.current_font_size: float = self.base_font_size
        self.box_height: float = self.char_height * 0.7
        self.line_height: float = self.char_height * 0.3

        # LOD override
        self._lod_max_mode: Optional[str] = None

        # Başlangıç durumu
        self._update_display_state()

    # ------------------------------------------------------------------
    # Zoom / char_width
    # ------------------------------------------------------------------

    def set_char_width(self, new_width: float) -> None:
        """
        Karakter genişliğini değiştirir (model tarafında) ve zoom'a bağlı
        font & display_mode state'ini günceller.
        """
        self.char_width = max(new_width, 0.001)
        self._update_display_state()

    def _update_display_state(self) -> None:
        """
        Zoom'a göre font boyutu ve display mode'u günceller.
        (Sadece sayısal state; QFont set etmek view'in işi.)
        """
        if self.default_char_width <= 0:
            self.default_char_width = 12.0

        cw = max(self.char_width, 0.001)
        base_cw = max(self.default_char_width, 0.001)
        scale = cw / base_cw

        # Font boyutu kademelendirme
        if scale >= 1.8:
            snapped_size = 12.0
        elif scale >= 1.2:
            snapped_size = 10.0
        elif scale >= 0.7:
            snapped_size = 8.0
        else:
            snapped_size = max(1.0, self.base_font_size * scale)

        self.current_font_size = snapped_size

        # Display mode
        if self.current_font_size >= self._TEXT_BOX_THRESHOLD:
            self.display_mode = self.TEXT_MODE
        elif self.current_font_size >= self._BOX_LINE_THRESHOLD:
            self.display_mode = self.BOX_MODE
        else:
            self.display_mode = self.LINE_MODE

        # Kutucuk / çizgi yükseklikleri
        box_reference_height = min(self.char_height * 0.7, self.current_font_size)
        self.box_height = max(box_reference_height, 1.0)
        self.line_height = self.char_height * 0.3

    # ------------------------------------------------------------------
    # Seçim
    # ------------------------------------------------------------------

    def set_selection(self, start_col: int, end_col: int) -> None:
        start = max(0, min(start_col, end_col))
        end = min(self.length, max(start_col, end_col) + 1)
        if start >= end:
            self.selection_range = None
        else:
            self.selection_range = (start, end)

    def clear_selection(self) -> None:
        self.selection_range = None

    # ------------------------------------------------------------------
    # LOD override
    # ------------------------------------------------------------------

    @staticmethod
    def _mode_order(mode: str) -> int:
        if mode == SequenceItemModel.TEXT_MODE:
            return 0
        if mode == SequenceItemModel.BOX_MODE:
            return 1
        return 2  # LINE_MODE

    def set_lod_max_mode(self, mode: Optional[str]) -> None:
        """
        View'dan gelebilecek LOD override.
        None: override yok.
        """
        if mode not in (None, self.TEXT_MODE, self.BOX_MODE, self.LINE_MODE):
            return
        self._lod_max_mode = mode

    def get_effective_mode(self) -> str:
        """
        LOD override'ı da hesaba katarak gerçek çizim modunu döner.
        """
        base_mode = self.display_mode
        if self._lod_max_mode is None:
            return base_mode

        if self._mode_order(base_mode) < self._mode_order(self._lod_max_mode):
            return self._lod_max_mode
        return base_mode
