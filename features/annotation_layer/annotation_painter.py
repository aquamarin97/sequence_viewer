# features/annotation_layer/annotation_painter.py
"""
Annotasyon şekil çizim fonksiyonları — v2 düzeltmeleri.

Değişiklikler
-------------
* FORWARD/REVERSE_PRIMER: dik üçgen (right-angled triangle).
  Üçgenin gövdeye bakan kenarı tam 90° dikey.
  Gövde ve uç aynı renk → yekpare görünüm.
* PROBE: strand parametresi eklendi.
  strand="+" → forward ok (sağa),  strand="-" → reverse ok (sola).
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor,
    QFont, QFontMetrics, QPolygonF,
)

_LABEL_MARGIN    = 4
_MIN_LABEL_W     = 20
_ARROW_TIP_RATIO = 0.18   # ok ucunun genişliğinin toplam genişliğe oranı


def draw_forward_primer(
    painter: QPainter,
    x: float, y: float, w: float, h: float,
    color: QColor, label: str,
) -> None:
    """
    Dik üçgen uçlu forward primer (→).
    Üçgenin SOL kenarı gövdeye tam 90° dikey.

         ┌────────────┐
         │            ├──►
         └────────────┘
    """
    if w <= 0:
        return

    tip_w  = min(w * _ARROW_TIP_RATIO, h * 0.9, 14.0)
    body_w = w - tip_w

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(color))

    # Gövde dikdörtgeni
    painter.drawRect(QRectF(x, y, body_w, h))

    # Dik üçgen:
    #   sol kenar → tam dikey (90°)
    #   tepe noktası → orta sağda (ok ucu)
    tip_base_x = x + body_w
    poly = QPolygonF([
        QPointF(tip_base_x,          y),           # sol üst (90° köşe)
        QPointF(tip_base_x + tip_w,  y + h / 2.0), # ok ucu
        QPointF(tip_base_x,          y + h),        # sol alt (90° köşe)
    ])
    painter.drawPolygon(poly)

    _draw_label(painter, x, y, body_w, h, label, color)


def draw_reverse_primer(
    painter: QPainter,
    x: float, y: float, w: float, h: float,
    color: QColor, label: str,
) -> None:
    """
    Dik üçgen uçlu reverse primer (←).
    Üçgenin SAĞ kenarı gövdeye tam 90° dikey.

    ◄──┌────────────┐
       └────────────┘
    """
    if w <= 0:
        return

    tip_w  = min(w * _ARROW_TIP_RATIO, h * 0.9, 14.0)
    body_x = x + tip_w
    body_w = w - tip_w

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(color))

    # Gövde
    painter.drawRect(QRectF(body_x, y, body_w, h))

    # Dik üçgen:
    #   sağ kenar → tam dikey (90°)
    #   tepe noktası → orta solda (ok ucu)
    poly = QPolygonF([
        QPointF(body_x,        y),            # sağ üst (90° köşe)
        QPointF(x,             y + h / 2.0),  # ok ucu
        QPointF(body_x,        y + h),         # sağ alt (90° köşe)
    ])
    painter.drawPolygon(poly)

    _draw_label(painter, body_x, y, body_w, h, label, color)


def draw_probe(
    painter: QPainter,
    x: float, y: float, w: float, h: float,
    color: QColor, label: str,
    strand: str = "+",
) -> None:
    """
    Probe — strand'a göre otomatik ok yönü.
    strand="+"  → forward ok (sağa, draw_forward_primer ile aynı)
    strand="-"  → reverse ok (sola, draw_reverse_primer ile aynı)
    """
    if strand == "-":
        draw_reverse_primer(painter, x, y, w, h, color, label)
    else:
        draw_forward_primer(painter, x, y, w, h, color, label)


def draw_region(
    painter: QPainter,
    x: float, y: float, w: float, h: float,
    color: QColor, label: str,
) -> None:
    """Yarı saydam bant + ince kenarlık."""
    if w <= 0:
        return
    fill   = QColor(color); fill.setAlpha(60)
    border = QColor(color); border.setAlpha(180)
    painter.setBrush(QBrush(fill))
    painter.setPen(QPen(border, 1.0))
    painter.drawRect(QRectF(x, y, w, h))
    _draw_label(painter, x, y, w, h, label, color)


# ---------------------------------------------------------------------------
# Yardımcı
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