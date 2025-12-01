# graphics/sequence_glyph_cache.py

from typing import Dict, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QFont, QColor, QPen, QPixmap, QFontMetrics


def default_nucleotide_color_map() -> Dict[str, QColor]:
    """
    Nt → renk mapping'i. A, T, C, G, gap, N vb.
    """
    return {
        "A": QColor(0, 180, 0),
        "T": QColor(200, 0, 0),
        "U": QColor(200, 0, 0),
        "C": QColor(0, 0, 200),
        "G": QColor(230, 140, 0),
        "-": QColor(150, 150, 150),
        "N": QColor(120, 120, 120),
    }


class GlyphCache:
    """
    TEXT_MODE için harfleri pixmap olarak cache'ler.

    Key: (char, font_family, font_point_size_int, bold, italic, r, g, b)
    Val: QPixmap (harfin tight bounding box'ına göre çizilmiş hali)
    """

    def __init__(self) -> None:
        self._cache: Dict[Tuple, QPixmap] = {}

    def get_glyph(self, ch: str, font: QFont, color: QColor) -> QPixmap:
        key = (
            ch,
            font.family(),
            int(round(font.pointSizeF() or font.pointSize())),
            font.bold(),
            font.italic(),
            color.red(),
            color.green(),
            color.blue(),
        )
        pm = self._cache.get(key)
        if pm is not None:
            return pm

        metrics = QFontMetrics(font)
        w = max(1, metrics.horizontalAdvance(ch))
        h = max(1, metrics.height())

        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)

        p = QPainter(pm)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        p.setFont(font)
        p.setPen(QPen(color))
        p.drawText(0, metrics.ascent(), ch)
        p.end()

        self._cache[key] = pm
        return pm


GLYPH_CACHE = GlyphCache()
