# sequence_viewer/features/header_viewer/header_viewer_model.py
from typing import List

class HeaderViewerModel:
    def __init__(self): self._headers: List[str] = []
    def add_header(self, text):
        self._headers.append(text); return len(self._headers) - 1
    def set_headers(self, headers):
        self._headers = list(headers)
    def set_header(self, index, text):
        if index < 0 or index >= len(self._headers):
            raise IndexError(f"Header index {index} out of range")
        self._headers[index] = text
    def remove_header(self, index):
        if index < 0 or index >= len(self._headers):
            raise IndexError(f"Header index {index} out of range")
        del self._headers[index]
    def move_header(self, from_index: int, to_index: int):
        n = len(self._headers)
        if not (0 <= from_index < n and 0 <= to_index < n):
            raise IndexError("move_header out of range")
        if from_index == to_index:
            return
        h = self._headers.pop(from_index)
        self._headers.insert(to_index, h)
    def clear_headers(self): self._headers.clear()
    def get_headers(self): return list(self._headers)
    def get_row_count(self): return len(self._headers)
    def get_header(self, index): return self._headers[index]
