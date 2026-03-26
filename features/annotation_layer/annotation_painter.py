# features/annotation_layer/annotation_painter.py
"""
Annotasyon şekil çizim fonksiyonları.

Her fonksiyon painter'ı kaydetmez/geri yüklemez —
çağıran taraf save/restore yapar.

Koordinatlar
------------
x       : sol kenar (viewport/scene px)
y       : üst kenar
w       : genişlik (px)
h       : yükseklik (px)
color   : QColor
label   : gösterilecek metin
painter : QPainter (aktif, uygun transform kurulu)
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QPolygonF,
)


# Sabitler
_ARROW_WIDTH   = 8    # ok başı genişliği (px)
_LABEL_MARGIN  = 4    # metin kenar boşluğu
_MIN_LABEL_W   = 20   # bu genişlikten dar olursa metin çizilmez


def draw_forward_primer(
    painter: QPainter,
    x: float, y: float, w: float, h: float,
    color: QColor, label: str,
) -> None:
    """
    ┌──────────────────────┐
    │  Label            ──►│
    └──────────────────────┘
    Ok başı sağda, içi dolu kutu.
    """
    if w <= 0:
        return

    arrow_w = min(_ARROW_WIDTH, w * 0.3)
    body_w  = w - arrow_w

    body_color  = color
    arrow_color = color.darker(120)

    # Gövde dikdörtgeni
    painter.setBrush(QBrush(body_color))
    painter.setPen(Qt.NoPen)
    painter.drawRect(QRectF(x, y, body_w, h))

    # Ok başı (dolu üçgen)
    tip_x  = x + w
    mid_y  = y + h / 2.0
    poly   = QPolygonF([
        QPointF(x + body_w, y),
        QPointF(tip_x,      mid_y),
        QPointF(x + body_w, y + h),
    ])
    painter.setBrush(QBrush(arrow_color))
    painter.drawPolygon(poly)

    # Etiket
    _draw_label(painter, x, y, w - arrow_w, h, label, color)


def draw_reverse_primer(
    painter: QPainter,
    x: float, y: float, w: float, h: float,
    color: QColor, label: str,
) -> None:
    """
    ┌──────────────────────┐
    │◄──             Label │
    └──────────────────────┘
    Ok başı solda.
    """
    if w <= 0:
        return

    arrow_w = min(_ARROW_WIDTH, w * 0.3)
    body_x  = x + arrow_w
    body_w  = w - arrow_w

    body_color  = color
    arrow_color = color.darker(120)

    # Gövde
    painter.setBrush(QBrush(body_color))
    painter.setPen(Qt.NoPen)
    painter.drawRect(QRectF(body_x, y, body_w, h))

    # Ok başı (dolu üçgen, sola bakan)
    tip_x = x
    mid_y = y + h / 2.0
    poly  = QPolygonF([
        QPointF(body_x, y),
        QPointF(tip_x,  mid_y),
        QPointF(body_x, y + h),
    ])
    painter.setBrush(QBrush(arrow_color))
    painter.drawPolygon(poly)

    # Etiket
    _draw_label(painter, body_x, y, body_w, h, label, color)


def draw_probe(
    painter: QPainter,
    x: float, y: float, w: float, h: float,
    color: QColor, label: str,
) -> None:
    """
    ┌──────────────────────┐
    │  Label               │  (ok yok, düz dikdörtgen)
    └──────────────────────┘
    """
    if w <= 0:
        return

    painter.setBrush(QBrush(color))
    painter.setPen(Qt.NoPen)
    painter.drawRect(QRectF(x, y, w, h))
    _draw_label(painter, x, y, w, h, label, color)


def draw_region(
    painter: QPainter,
    x: float, y: float, w: float, h: float,
    color: QColor, label: str,
) -> None:
    """
    Yarı saydam bant + ince kenarlık.
    """
    if w <= 0:
        return

    fill = QColor(color)
    fill.setAlpha(60)                     # yarı saydam dolgu
    border = QColor(color)
    border.setAlpha(180)

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
    """
    Şeklin içine sığıyorsa etiket yazar.
    Renk parlaklığına göre metin rengi otomatik seçilir (okunabilirlik).
    """
    if not label or w < _MIN_LABEL_W:
        return

    # Metin rengi: arkaplan koyu ise beyaz, açık ise siyah
    lum = 0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()
    text_color = QColor(255, 255, 255) if lum < 140 else QColor(20, 20, 20)

    font = QFont("Arial", 7)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QPen(text_color))

    metrics   = QFontMetrics(font)
    text_rect = QRectF(
        x + _LABEL_MARGIN,
        y,
        w - _LABEL_MARGIN * 2,
        h,
    )

    # Sığmıyorsa elidle
    elided = metrics.elidedText(label, Qt.ElideRight, int(text_rect.width()))
    painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)