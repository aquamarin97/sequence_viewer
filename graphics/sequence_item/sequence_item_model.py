from typing import Optional, Tuple, Dict
from PyQt5.QtGui import QColor
from graphics.sequence_item.sequence_glyph_cache import default_nucleotide_color_map

class SequenceItemModel:
    TEXT_MODE = "text"
    BOX_MODE = "box"
    LINE_MODE = "line"
    _TEXT_BOX_THRESHOLD = 8.0
    _BOX_LINE_THRESHOLD = 5.0

    def __init__(self, sequence, char_width=12.0, char_height=18.0, color_map=None):
        self.sequence = sequence
        self.sequence_upper = sequence.upper()
        self.length = len(sequence)
        self.char_width = max(char_width, 0.001)
        self.char_height = max(1, int(round(char_height)))
        self._custom_color_map = color_map is not None
        self.color_map = color_map or default_nucleotide_color_map()
        self.default_char_width = self.char_width
        self.selection_range = None
        self.base_font_size = self.char_height * 0.6
        self.display_mode = self.TEXT_MODE
        self.current_font_size = self.base_font_size
        self.box_height = self.char_height * 0.7
        self.line_height = self.char_height * 0.3
        self._lod_max_mode = None
        self._update_display_state()

    def refresh_color_map(self):
        if not self._custom_color_map:
            self.color_map = default_nucleotide_color_map()

    def set_char_width(self, new_width):
        self.char_width = max(new_width, 0.001)
        self._update_display_state()

    def _update_display_state(self):
        from settings.display_settings_manager import display_settings_manager
        if self.default_char_width <= 0: self.default_char_width = 12.0
        cw = max(self.char_width, 0.001)
        base_cw = max(self.default_char_width, 0.001)
        scale = cw / base_cw
        max_fs = float(display_settings_manager.sequence_font_size)
        if scale >= 1.8: snapped_size = max_fs
        elif scale >= 1.2: snapped_size = max(1.0, max_fs * (10.0 / 12.0))
        elif scale >= 0.7: snapped_size = max(1.0, max_fs * (8.0 / 12.0))
        else: snapped_size = max(1.0, self.base_font_size * scale)
        self.current_font_size = snapped_size
        if self.current_font_size >= self._TEXT_BOX_THRESHOLD: self.display_mode = self.TEXT_MODE
        elif self.current_font_size >= self._BOX_LINE_THRESHOLD: self.display_mode = self.BOX_MODE
        else: self.display_mode = self.LINE_MODE
        box_ref = min(self.char_height * 0.7, self.current_font_size)
        self.box_height = max(box_ref, 1.0)
        self.line_height = self.char_height * 0.3

    def set_selection(self, start_col, end_col):
        start = max(0, min(start_col, end_col))
        end = min(self.length, max(start_col, end_col) + 1)
        self.selection_range = (start, end) if start < end else None

    def clear_selection(self): self.selection_range = None

    @staticmethod
    def _mode_order(mode):
        if mode == SequenceItemModel.TEXT_MODE: return 0
        if mode == SequenceItemModel.BOX_MODE: return 1
        return 2

    def set_lod_max_mode(self, mode):
        if mode not in (None, self.TEXT_MODE, self.BOX_MODE, self.LINE_MODE): return
        self._lod_max_mode = mode

    def get_effective_mode(self):
        base_mode = self.display_mode
        if self._lod_max_mode is None: return base_mode
        if self._mode_order(base_mode) < self._mode_order(self._lod_max_mode): return self._lod_max_mode
        return base_mode
