# features/annotation_layer/annotation_painter.py
"""
Annotation şekil çizim fonksiyonları.

Şekil: Dik Yamuk (Right Trapezoid)
------------------------------------
PRIMER ve PROBE için kullanılan şekil, 30-60-90 üçgen oranlarına sahip
bir dik yamuğun dikdörtgen gövdeye eklenmesiyle oluşur.

Geometri (Forward +):

    (0,0)──────────(body_w, 0)
      │                  /   ← slant 60° yataydan / 30° dikeyde
      │                   \
      │                    \
    (0,h)──────────────────(w, h)   ← tip (en sağ nokta)

    tip_w = h / √3   → 60°/30° oranı
    body_w = w − tip_w  (0'a inebilir → saf üçgen, yön korunur)

Zoom-out garantisi:
    tip_w ≥ _MIN_TIP_W  → her zoom seviyesinde yön görünür.
    body_w = 0 olduğunda şekil otomatik olarak üçgene dejenere olur.

Reverse (−): forward'ın yatay yansıması.

REPEATED_REGION: yarı saydam dikdörtgen.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor,
    QFont, QFontMetrics, QPolygonF,
)

# --- Sabitler ---
_LABEL_MARGIN = 4
_MIN_LABEL_W  = 16

# Tip (ok ucu) her zoom seviyesinde görünür kalmak için minimum piksel genişliği.
# Zoom-out'ta char_width küçüldükçe tip de küçülür; ama asla bu değerin altına inmez.
_MIN_TIP_PX = 5.0


# ---------------------------------------------------------------------------
# PRIMER
# ---------------------------------------------------------------------------

def draw_primer(
    painter: QPainter,
    x: float, y: float, w: float, h: float,
    color: QColor, label: str,
    strand: str = "+",
    char_width: float = 12.0,
) -> None:
    """
    Dik yamuk şeklinde primer.

    tip_w = char_width (1 nükleotid hücresi) — zoom ile birlikte ölçeklenir,
    yön her zoom seviyesinde tutarlı kalır.
    body_w = 0 olduğunda şekil üçgene dejenere olur.

    Forward (+): sol dik kenar, sağa uzayan taban → sağa yönelik.
    Reverse (−): sağ dik kenar, sola uzayan taban → sola yönelik.
    """
    if w <= 0:
        return

    # tip_w = 2 nükleotid genişliği; zoom-out'ta _MIN_TIP_PX garantisi.
    # body_w = 0 → saf üçgen (yön her zaman korunur).
    tip_w  = min(max(2.0 * char_width, _MIN_TIP_PX), w)
    body_w = max(0.0, w - tip_w)

    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(color))

    if strand == "+":
        # Forward: sol dik kenar, sağa yönelik üçgen uç
        poly = QPolygonF([
            QPointF(x,           y),      # TL  (90°)
            QPointF(x + body_w,  y),      # TR  (gövde-uç birleşimi)
            QPointF(x + w,       y + h),  # tip (sağ alt)
            QPointF(x,           y + h),  # BL  (90°)
        ])
        label_x = x
        label_w = body_w
    else:
        # Reverse: sağ dik kenar, sola yönelik üçgen uç
        poly = QPolygonF([
            QPointF(x + tip_w,   y),      # TL  (gövde-uç birleşimi)
            QPointF(x + w,       y),      # TR  (90°)
            QPointF(x + w,       y + h),  # BR  (90°)
            QPointF(x,           y + h),  # tip (sol alt)
        ])
        label_x = x + tip_w
        label_w = body_w

    painter.drawPolygon(poly)
    if label_w >= _MIN_LABEL_W:
        _draw_label(painter, label_x, y, label_w, h, label, color)


# ---------------------------------------------------------------------------
# PROBE
# ---------------------------------------------------------------------------

def draw_probe(
    painter: QPainter,
    x: float, y: float, w: float, h: float,
    color: QColor, label: str,
    strand: str = "+",
    char_width: float = 12.0,
) -> None:
    """
    Primer ile aynı dik yamuk geometrisi; dolgu biraz daha şeffaf,
    kenarlık eklenmiş → primer'dan görsel olarak ayırt edilebilir.
    tip_w = char_width (1 nükleotid hücresi).
    """
    if w <= 0:
        return

    tip_w  = min(max(2.0 * char_width, _MIN_TIP_PX), w)
    body_w = max(0.0, w - tip_w)

    fill    = QColor(color); fill.setAlpha(170)
    outline = QColor(color)

    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setBrush(QBrush(fill))
    painter.setPen(QPen(outline, 1.5))

    if strand == "+":
        poly = QPolygonF([
            QPointF(x,           y),
            QPointF(x + body_w,  y),
            QPointF(x + w,       y + h),
            QPointF(x,           y + h),
        ])
        label_x = x
        label_w = body_w
    else:
        poly = QPolygonF([
            QPointF(x + tip_w,   y),
            QPointF(x + w,       y),
            QPointF(x + w,       y + h),
            QPointF(x,           y + h),
        ])
        label_x = x + tip_w
        label_w = body_w

    painter.drawPolygon(poly)
    if label_w >= _MIN_LABEL_W:
        _draw_label(painter, label_x, y, label_w, h, label, color)


# ---------------------------------------------------------------------------
# REPEATED REGION
# ---------------------------------------------------------------------------

def draw_repeated_region(
    painter: QPainter,
    x: float, y: float, w: float, h: float,
    color: QColor, label: str,
) -> None:
    """Yarı saydam dikdörtgen — yön taşımaz, alt şeritte render edilir."""
    if w <= 0:
        return
    fill   = QColor(color); fill.setAlpha(60)
    border = QColor(color); border.setAlpha(180)
    painter.setRenderHint(QPainter.Antialiasing, False)
    painter.setBrush(QBrush(fill))
    painter.setPen(QPen(border, 1.0))
    painter.drawRect(QRectF(x, y, w, h))
    _draw_label(painter, x, y, w, h, label, color)


# ---------------------------------------------------------------------------
# Yardımcı: etiket çizimi
# ---------------------------------------------------------------------------

def _draw_label(
    painter: QPainter,
    x: float, y: float, w: float, h: float,
    label: str, bg_color: QColor,
) -> None:
    if not label or w < _MIN_LABEL_W:
        return
    lum = (0.299 * bg_color.red()
           + 0.587 * bg_color.green()
           + 0.114 * bg_color.blue())
    text_color = QColor(255, 255, 255) if lum < 140 else QColor(20, 20, 20)
    font = QFont("Arial", 7)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QPen(text_color))
    metrics   = QFontMetrics(font)
    text_rect = QRectF(x + _LABEL_MARGIN, y, w - _LABEL_MARGIN * 2, h)
    elided    = metrics.elidedText(label, Qt.ElideRight, int(text_rect.width()))
    painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)