# features/header_viewer/header_viewer_model.py
from typing import List

class HeaderViewerModel:
    def __init__(self): self._headers = []
    def add_header(self, text):
        self._headers.append(text); return len(self._headers) - 1
    def clear_headers(self): self._headers.clear()
    def get_headers(self): return list(self._headers)
    def get_row_count(self): return len(self._headers)
    def get_header(self, index): return self._headers[index]


