from typing import Dict, Tuple
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QFont, QColor, QPen, QPixmap, QFontMetrics

def default_nucleotide_color_map():
    from settings.color_styles import color_style_manager
    return color_style_manager.nucleotide_color_map()

class GlyphCache:
    def __init__(self): self._cache = {}
    def invalidate(self): self._cache.clear()
    def get_glyph(self, ch, font, color):
        key = (ch, font.family(), int(round(font.pointSizeF() or font.pointSize())), font.bold(), font.italic(), color.red(), color.green(), color.blue())
        pm = self._cache.get(key)
        if pm is not None: return pm
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

def _on_styles_changed(): GLYPH_CACHE.invalidate()
try:
    from settings.color_styles import color_style_manager
    color_style_manager.stylesChanged.connect(_on_styles_changed)
except: pass
