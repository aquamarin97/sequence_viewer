# graphics/sequence_glyph_cache.py

from typing import Dict, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QFont, QColor, QPen, QPixmap, QFontMetrics


def default_nucleotide_color_map() -> Dict[str, QColor]:
    """
    Nt → renk mapping'i — color_style_manager'dan alınır.
    Kullanıcı renk tercihlerini Settings üzerinden değiştirdiğinde
    otomatik olarak güncellenir.
    """
    from settings.color_styles import color_style_manager
    return color_style_manager.nucleotide_color_map()


class GlyphCache:
    """
    TEXT_MODE için harfleri pixmap olarak cache'ler.

    Key: (char, font_family, font_point_size_int, bold, italic, r, g, b)
    Val: QPixmap (harfin tight bounding box'ına göre çizilmiş hali)

    Not: color_style_manager.stylesChanged sinyali geldiğinde cache
    temizlenmelidir. Bkz. GLYPH_CACHE.invalidate().
    """

    def __init__(self) -> None:
        self._cache: Dict[Tuple, QPixmap] = {}

    def invalidate(self) -> None:
        """Renk değiştiğinde tüm cache'i temizle."""
        self._cache.clear()

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

# Renk stili değiştiğinde glyph cache'i otomatik temizle
def _on_styles_changed():
    GLYPH_CACHE.invalidate()

try:
    from settings.color_styles import color_style_manager
    color_style_manager.stylesChanged.connect(_on_styles_changed)
except Exception:
    pass   # Uygulama henüz başlatılmamışsa sessizce geç