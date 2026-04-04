# features/annotation_layer/annotation_painter.py
from __future__ import annotations
import math
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics,
    QPainterPath, QLinearGradient,
)
from model.annotation import AnnotationType
from settings.annotation_styles import annotation_style_manager
from settings.theme import theme_manager

_LABEL_MARGIN  = 4
_MIN_TIP_PX    = 5.0
_CORNER_RADIUS = 3.5      # köşe yuvarlaması yarıçapı (px)

# ── Label metin renkleri ───────────────────────────────────────────────────────
# Luminance < 140 → koyu zemin → beyaz metin; aksi halde koyu metin.
_LABEL_TEXT_ON_DARK  = QColor(255, 255, 255)
_LABEL_TEXT_ON_LIGHT = QColor(20,  20,  20)


# ── Renk yardımcıları ──────────────────────────────────────────────────────────

def _clamp(v):
    return max(0, min(255, v))


def _make_gradient(x, y, h, base_color, fill_alpha, is_dark):
    """
    Annotation renginden türetilmiş dikey QLinearGradient.

    Üst highlight → orta baz → alt shadow tonlaması;
    dark modda highlight daha belirgin, light modda daha yumuşak.
    """
    d_hi  = 48 if is_dark else 28
    d_sha = 38 if is_dark else 22

    top = QColor(
        _clamp(base_color.red()   + d_hi),
        _clamp(base_color.green() + d_hi),
        _clamp(base_color.blue()  + d_hi),
        fill_alpha,
    )
    mid = QColor(base_color.red(), base_color.green(), base_color.blue(), fill_alpha)
    bot = QColor(
        _clamp(base_color.red()   - d_sha),
        _clamp(base_color.green() - d_sha),
        _clamp(base_color.blue()  - d_sha),
        fill_alpha,
    )

    grad = QLinearGradient(x, y, x, y + h)
    grad.setColorAt(0.00, top)
    grad.setColorAt(0.42, mid)
    grad.setColorAt(1.00, bot)
    return grad


def _make_border_color(base_color, border_alpha):
    """Kenarlık için baz renginin koyu tonu."""
    d = 55
    return QColor(
        _clamp(base_color.red()   - d),
        _clamp(base_color.green() - d),
        _clamp(base_color.blue()  - d),
        border_alpha,
    )


# ── Köşe yuvarlama ─────────────────────────────────────────────────────────────

def _rounded_poly_path(points, radius):
    """
    Köşeleri quadratic Bezier eğrisiyle yuvarlatılmış çokgen QPainterPath'i.

    Her köşede kontrol noktası orijinal vertex, eğri komşu kenarlar üzerinde
    başlar/biter. Kısa kenarlarda yarıçap otomatik küçülür — tip ucun sivri
    formu korunur.
    """
    path = QPainterPath()
    n = len(points)

    for i in range(n):
        prev_p = points[(i - 1) % n]
        curr_p = points[i]
        next_p = points[(i + 1) % n]

        v_in_x  = prev_p.x() - curr_p.x()
        v_in_y  = prev_p.y() - curr_p.y()
        v_out_x = next_p.x() - curr_p.x()
        v_out_y = next_p.y() - curr_p.y()

        len_in  = math.hypot(v_in_x,  v_in_y)
        len_out = math.hypot(v_out_x, v_out_y)

        r = min(radius, len_in / 2.0, len_out / 2.0)

        if r < 0.5 or len_in == 0 or len_out == 0:
            if i == 0:
                path.moveTo(curr_p)
            else:
                path.lineTo(curr_p)
            continue

        arc_in  = QPointF(curr_p.x() + (v_in_x  / len_in)  * r,
                          curr_p.y() + (v_in_y  / len_in)  * r)
        arc_out = QPointF(curr_p.x() + (v_out_x / len_out) * r,
                          curr_p.y() + (v_out_y / len_out) * r)

        if i == 0:
            path.moveTo(arc_in)
        else:
            path.lineTo(arc_in)

        path.quadTo(curr_p, arc_out)

    path.closeSubpath()
    return path


# ── Ana çizim fonksiyonları ────────────────────────────────────────────────────

def draw_primer(painter, x, y, w, h, color, label, strand="+",
                char_width=12.0, style_mode="default"):
    """
    Primer annotation'ı çizer.

    Parameters
    ----------
    style_mode : str
        "default" — mevcut görsel stil.
        İleride "academic" eklenecektir (kapsam dışı).
    """
    if w <= 0:
        return

    tip_w  = min(max(2.0 * char_width, _MIN_TIP_PX), w)
    body_w = max(0.0, w - tip_w)
    style  = annotation_style_manager.get(AnnotationType.PRIMER)
    is_dark = theme_manager.current.name == "dark"

    painter.setRenderHint(QPainter.Antialiasing, True)

    if strand == "+":
        pts = [
            QPointF(x,          y),
            QPointF(x + body_w, y),
            QPointF(x + w,      y + h),
            QPointF(x,          y + h),
        ]
        label_x, label_w = x, body_w
    else:
        pts = [
            QPointF(x + tip_w,  y),
            QPointF(x + w,      y),
            QPointF(x + w,      y + h),
            QPointF(x,          y + h),
        ]
        label_x, label_w = x + tip_w, body_w

    path = _rounded_poly_path(pts, _CORNER_RADIUS)
    grad = _make_gradient(x, y, h, color, style.fill_alpha, is_dark)

    painter.setBrush(QBrush(grad))
    if style.border_width > 0 and style.border_alpha > 0:
        painter.setPen(QPen(_make_border_color(color, style.border_alpha),
                            style.border_width))
    else:
        painter.setPen(Qt.NoPen)
    painter.drawPath(path)

    if label_w >= style.label_min_width:
        _draw_label(painter, label_x, y, label_w, h, label, color,
                    font_size=style.label_font_size,
                    font_family=style.label_font_family)


def draw_probe(painter, x, y, w, h, color, label, strand="+",
               char_width=12.0, style_mode="default"):
    """
    Probe annotation'ı çizer.

    Parameters
    ----------
    style_mode : str
        "default" — mevcut görsel stil.
        İleride "academic" eklenecektir (kapsam dışı).
    """
    if w <= 0:
        return

    tip_w  = min(max(2.0 * char_width, _MIN_TIP_PX), w)
    body_w = max(0.0, w - tip_w)
    style  = annotation_style_manager.get(AnnotationType.PROBE)
    is_dark = theme_manager.current.name == "dark"

    painter.setRenderHint(QPainter.Antialiasing, True)

    if strand == "+":
        pts = [
            QPointF(x,          y),
            QPointF(x + body_w, y),
            QPointF(x + w,      y + h),
            QPointF(x,          y + h),
        ]
        label_x, label_w = x, body_w
    else:
        pts = [
            QPointF(x + tip_w,  y),
            QPointF(x + w,      y),
            QPointF(x + w,      y + h),
            QPointF(x,          y + h),
        ]
        label_x, label_w = x + tip_w, body_w

    path = _rounded_poly_path(pts, _CORNER_RADIUS)
    grad = _make_gradient(x, y, h, color, style.fill_alpha, is_dark)

    painter.setBrush(QBrush(grad))
    painter.setPen(QPen(_make_border_color(color, style.border_alpha),
                        style.border_width))
    painter.drawPath(path)

    if label_w >= style.label_min_width:
        _draw_label(painter, label_x, y, label_w, h, label, color,
                    font_size=style.label_font_size,
                    font_family=style.label_font_family)


def draw_repeated_region(painter, x, y, w, h, color, label, style_mode="default"):
    """
    Repeated region annotation'ı çizer.

    Parameters
    ----------
    style_mode : str
        "default" — mevcut görsel stil.
        İleride "academic" eklenecektir (kapsam dışı).
    """
    if w <= 0:
        return

    style   = annotation_style_manager.get(AnnotationType.REPEATED_REGION)
    is_dark = theme_manager.current.name == "dark"

    painter.setRenderHint(QPainter.Antialiasing, True)

    path = QPainterPath()
    path.addRoundedRect(QRectF(x, y, w, h), _CORNER_RADIUS, _CORNER_RADIUS)
    grad = _make_gradient(x, y, h, color, style.fill_alpha, is_dark)

    painter.setBrush(QBrush(grad))
    painter.setPen(QPen(_make_border_color(color, style.border_alpha),
                        style.border_width))
    painter.drawPath(path)

    if w >= style.label_min_width:
        _draw_label(painter, x, y, w, h, label, color,
                    font_size=style.label_font_size,
                    font_family=style.label_font_family)


# ── Label ──────────────────────────────────────────────────────────────────────

def _draw_label(painter, x, y, w, h, label, bg_color, font_size=7, font_family="Arial"):
    if not label or w < 4:
        return
    lum        = 0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()
    text_color = _LABEL_TEXT_ON_DARK if lum < 140 else _LABEL_TEXT_ON_LIGHT
    font       = QFont(font_family, max(6, font_size))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QPen(text_color))
    metrics   = QFontMetrics(font)
    text_rect = QRectF(x + _LABEL_MARGIN, y, w - _LABEL_MARGIN * 2, h)
    elided    = metrics.elidedText(label, Qt.ElideRight, int(text_rect.width()))
    painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignHCenter, elided)
