from __future__ import annotations
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QPolygonF
from model.annotation import AnnotationType
from settings.annotation_styles import annotation_style_manager

_LABEL_MARGIN = 4
_MIN_TIP_PX = 5.0

# ── Annotation Etiket Metin Renkleri ─────────────────────────────────────────
# Arka plan parlaklığına (luminance) göre okunabilirlik için seçilen kontrast renkler.
# Luminance < 140 → koyu zemin → beyaz metin; aksi halde koyu metin.
_LABEL_TEXT_ON_DARK  = QColor(255, 255, 255)   # beyaz — koyu arka plan üzeri
_LABEL_TEXT_ON_LIGHT = QColor(20,  20,  20)    # neredeyse siyah — açık arka plan üzeri

def draw_primer(painter, x, y, w, h, color, label, strand="+", char_width=12.0):
    if w <= 0: return
    tip_w = min(max(2.0 * char_width, _MIN_TIP_PX), w)
    body_w = max(0.0, w - tip_w)
    style = annotation_style_manager.get(AnnotationType.PRIMER)
    fill = QColor(color); fill.setAlpha(style.fill_alpha)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setBrush(QBrush(fill))
    if style.border_width > 0 and style.border_alpha > 0:
        border = QColor(color); border.setAlpha(style.border_alpha)
        painter.setPen(QPen(border, style.border_width))
    else: painter.setPen(Qt.NoPen)
    if strand == "+":
        poly = QPolygonF([QPointF(x,y),QPointF(x+body_w,y),QPointF(x+w,y+h),QPointF(x,y+h)])
        label_x, label_w = x, body_w
    else:
        poly = QPolygonF([QPointF(x+tip_w,y),QPointF(x+w,y),QPointF(x+w,y+h),QPointF(x,y+h)])
        label_x, label_w = x+tip_w, body_w
    painter.drawPolygon(poly)
    if label_w >= style.label_min_width:
        _draw_label(painter, label_x, y, label_w, h, label, color, font_size=style.label_font_size)

def draw_probe(painter, x, y, w, h, color, label, strand="+", char_width=12.0):
    if w <= 0: return
    tip_w = min(max(2.0 * char_width, _MIN_TIP_PX), w)
    body_w = max(0.0, w - tip_w)
    style = annotation_style_manager.get(AnnotationType.PROBE)
    fill = QColor(color); fill.setAlpha(style.fill_alpha)
    outline = QColor(color); outline.setAlpha(style.border_alpha)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setBrush(QBrush(fill)); painter.setPen(QPen(outline, style.border_width))
    if strand == "+":
        poly = QPolygonF([QPointF(x,y),QPointF(x+body_w,y),QPointF(x+w,y+h),QPointF(x,y+h)])
        label_x, label_w = x, body_w
    else:
        poly = QPolygonF([QPointF(x+tip_w,y),QPointF(x+w,y),QPointF(x+w,y+h),QPointF(x,y+h)])
        label_x, label_w = x+tip_w, body_w
    painter.drawPolygon(poly)
    if label_w >= style.label_min_width:
        _draw_label(painter, label_x, y, label_w, h, label, color, font_size=style.label_font_size)

def draw_repeated_region(painter, x, y, w, h, color, label):
    if w <= 0: return
    style = annotation_style_manager.get(AnnotationType.REPEATED_REGION)
    fill = QColor(color); fill.setAlpha(style.fill_alpha)
    border = QColor(color); border.setAlpha(style.border_alpha)
    painter.setRenderHint(QPainter.Antialiasing, False)
    painter.setBrush(QBrush(fill)); painter.setPen(QPen(border, style.border_width))
    painter.drawRect(QRectF(x, y, w, h))
    if w >= style.label_min_width:
        _draw_label(painter, x, y, w, h, label, color, font_size=style.label_font_size)

def _draw_label(painter, x, y, w, h, label, bg_color, font_size=7):
    if not label or w < 4: return
    lum = 0.299*bg_color.red() + 0.587*bg_color.green() + 0.114*bg_color.blue()
    text_color = _LABEL_TEXT_ON_DARK if lum < 140 else _LABEL_TEXT_ON_LIGHT
    font = QFont("Arial", max(6, font_size)); font.setBold(True)
    painter.setFont(font); painter.setPen(QPen(text_color))
    metrics = QFontMetrics(font)
    text_rect = QRectF(x+_LABEL_MARGIN, y, w-_LABEL_MARGIN*2, h)
    elided = metrics.elidedText(label, Qt.ElideRight, int(text_rect.width()))
    painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)
