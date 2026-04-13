# features/annotation_layer/annotation_painter.py
from __future__ import annotations
import math
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QFontMetricsF,
    QPainterPath, QLinearGradient,
)
from sequence_viewer.model.annotation import AnnotationType
from sequence_viewer.settings.annotation_styles import annotation_style_manager
from sequence_viewer.settings.theme import theme_manager

_LABEL_MARGIN = 6      # yatay iÃ§ boÅŸluk (px)
_MIN_TIP_PX   = 5.0
_CORNER_RADIUS   = 3.5    # kÃ¶ÅŸe yuvarlamasÄ± yarÄ±Ã§apÄ± (px)

# â”€â”€ Label metin renkleri â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Luminance < 140 â†’ koyu zemin â†’ beyaz metin; aksi halde koyu metin.
_LABEL_TEXT_ON_DARK  = QColor(255, 255, 255)
_LABEL_TEXT_ON_LIGHT = QColor(20,  20,  20)


# â”€â”€ Renk yardÄ±mcÄ±larÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _clamp(v):
    return max(0, min(255, v))


def _make_gradient(x, y, h, base_color, fill_alpha, is_dark):
    """
    Annotation renginden tÃ¼retilmiÅŸ dikey QLinearGradient.

    Ãœst highlight â†’ orta baz â†’ alt shadow tonlamasÄ±;
    dark modda highlight daha belirgin, light modda daha yumuÅŸak.
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
    """KenarlÄ±k iÃ§in baz renginin koyu tonu."""
    d = 55
    return QColor(
        _clamp(base_color.red()   - d),
        _clamp(base_color.green() - d),
        _clamp(base_color.blue()  - d),
        border_alpha,
    )


# â”€â”€ KÃ¶ÅŸe yuvarlama â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _rounded_poly_path(points, radius):
    """
    KÃ¶ÅŸeleri quadratic Bezier eÄŸrisiyle yuvarlatÄ±lmÄ±ÅŸ Ã§okgen QPainterPath'i.

    Her kÃ¶ÅŸede kontrol noktasÄ± orijinal vertex, eÄŸri komÅŸu kenarlar Ã¼zerinde
    baÅŸlar/biter. KÄ±sa kenarlarda yarÄ±Ã§ap otomatik kÃ¼Ã§Ã¼lÃ¼r â€” tip ucun sivri
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


# â”€â”€ Ana Ã§izim fonksiyonlarÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def draw_primer(painter, x, y, w, h, color, label, strand="+",
                char_width=12.0, style_mode="default"):
    """
    Primer annotation'Ä± Ã§izer.

    Parameters
    ----------
    style_mode : str
        "default" â€” mevcut gÃ¶rsel stil.
        Ä°leride "academic" eklenecektir (kapsam dÄ±ÅŸÄ±).
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
    Probe annotation'Ä± Ã§izer.

    Parameters
    ----------
    style_mode : str
        "default" â€” mevcut gÃ¶rsel stil.
        Ä°leride "academic" eklenecektir (kapsam dÄ±ÅŸÄ±).
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
    Repeated region annotation'Ä± Ã§izer.

    Parameters
    ----------
    style_mode : str
        "default" â€” mevcut gÃ¶rsel stil.
        Ä°leride "academic" eklenecektir (kapsam dÄ±ÅŸÄ±).
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


_MM_V_PAD = 1        # marker ile lane Ã¼st/alt kenarÄ± arasÄ±ndaki dikey boÅŸluk (px)
_MM_TEXT_THRESHOLD   = 8.0   # bu char_width'in altÄ±nda â†’ box/line mod, metin gizlenir
_MM_FULL_FONT_CW     = 12.0  # bu char_width'in Ã¼stÃ¼nde â†’ tam font boyutu


def draw_mismatch_marker(painter, x, y, w, h, color, label,
                          char_width=12.0, font_family=None, font_size=None):
    """
    Mismatch marker alt-annotation'Ä± Ã§izer.

    Parameters
    ----------
    label       : GÃ¶sterilecek tek karakter (beklenen NA / expected base).
    char_width  : Mevcut karakter geniÅŸliÄŸi (px).
    font_family : Metin iÃ§in font ailesi; None â†’ annotation style varsayÄ±lanÄ±.
    font_size   : BaÄŸlam iÃ§in MAKSIMUM (base) font boyutu (pt).
                  Scaling bu fonksiyon iÃ§inde char_width'e gÃ¶re hesaplanÄ±r;
                  Ã§aÄŸÄ±ran her zaman base (zoom-independent) deÄŸeri geÃ§melidir.
    """
    if w <= 0 or h <= 0:
        return
    style = annotation_style_manager.get(AnnotationType.MISMATCH_MARKER)

    # Dikey padding â€” box lane kenarlarÄ±ndan gÃ¶rsel boÅŸluk
    box_y = y + _MM_V_PAD
    box_h = max(1.0, h - 2 * _MM_V_PAD)
    box_left = int(round(x))
    box_top = int(round(box_y))
    box_right = max(box_left + 1, int(round(x + w)))
    box_bottom = max(box_top + 1, int(round(box_y + box_h)))
    box_rect = QRectF(box_left, box_top, box_right - box_left, box_bottom - box_top)

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)

    path = QPainterPath()
    path.addRoundedRect(box_rect, _CORNER_RADIUS, _CORNER_RADIUS)

    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(Qt.NoPen)   # Border yok; seÃ§im durumunda draw_selection_outline kullanÄ±lÄ±r
    painter.drawPath(path)

    # Metin: sadece text modunda (char_width yeterince bÃ¼yÃ¼kse) gÃ¶ster
    show_text = char_width >= _MM_TEXT_THRESHOLD
    if show_text and label:
        bg = QColor(color)
        lum = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
        text_color = _LABEL_TEXT_ON_DARK if lum < 140 else _LABEL_TEXT_ON_LIGHT
        ff = font_family if font_family else style.label_font_family
        base_fs = float(font_size) if font_size else float(style.label_font_size)

        # Sequence viewer ile aynÄ± LOD adÄ±mlarÄ±:
        #   char_width >= 12 â†’ tam boyut  (SequenceItemModel scale >= 1.8)
        #   char_width >=  8 â†’ 10/12 oranÄ± (scale >= 1.2, text mod alt sÄ±nÄ±rÄ±)
        if char_width >= _MM_FULL_FONT_CW:
            effective_fs = base_fs
        else:
            effective_fs = max(6.0, base_fs * (10.0 / 12.0))

        font = QFont(ff)
        font.setPointSizeF(max(6.0, effective_fs))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(text_color))
        ch = label[0]
        # Point/baseline tabanlÄ± Ã§izim max zoom-out'ta alt-piksel snap nedeniyle
        # hafif sola kaymÄ±ÅŸ gÃ¶rÃ¼nebiliyor; rect iÃ§i merkezleme daha kararlÄ±.
        painter.drawText(box_rect, Qt.AlignCenter, ch)

    painter.restore()


# â”€â”€ SeÃ§im ve hover outline â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _build_primer_probe_path(x, y, w, h, strand, char_width):
    tip_w  = min(max(2.0 * char_width, _MIN_TIP_PX), w)
    body_w = max(0.0, w - tip_w)
    if strand == "+":
        pts = [QPointF(x, y), QPointF(x + body_w, y),
               QPointF(x + w, y + h), QPointF(x, y + h)]
    else:
        pts = [QPointF(x + tip_w, y), QPointF(x + w, y),
               QPointF(x + w, y + h), QPointF(x, y + h)]
    return _rounded_poly_path(pts, _CORNER_RADIUS)


def _build_repeated_region_path(x, y, w, h):
    path = QPainterPath()
    path.addRoundedRect(QRectF(x, y, w, h), _CORNER_RADIUS, _CORNER_RADIUS)
    return path


def _selection_colors(base_color):
    """
    Annotation renginden seÃ§im halo ve iÃ§ kenar renklerini tÃ¼retir.

    Halo: annotation renginin doygunluÄŸu artÄ±rÄ±lmÄ±ÅŸ, parlatÄ±lmÄ±ÅŸ versiyonu.
    Kenar: annotation rengine gÃ¶re kontrast saÄŸlayan beyaz ya da koyu ton.
    """
    h = base_color.hsvHueF()
    s = min(1.0, base_color.hsvSaturationF() * 1.15 + 0.25)
    # ParlaklÄ±k: koyu renkler iÃ§in daha aydÄ±nlÄ±k, zaten aÃ§Ä±k renkler iÃ§in koru
    v_base = base_color.valueF()
    v_halo = min(1.0, v_base * 0.6 + 0.55)
    halo = QColor.fromHsvF(h if h >= 0 else 0.0, s, v_halo, 0.72)
    # Ä°Ã§ kenar: luminans yÃ¼ksekse koyu, dÃ¼ÅŸÃ¼kse beyaz
    lum = 0.299 * base_color.red() + 0.587 * base_color.green() + 0.114 * base_color.blue()
    inner = QColor(20, 20, 20, 210) if lum > 160 else QColor(255, 255, 255, 220)
    return halo, inner


def draw_selection_outline(painter, x, y, w, h, ann_type, base_color,
                           strand="+", char_width=12.0):
    """
    SeÃ§ili annotation iÃ§in annotation renginden tÃ¼retilmiÅŸ parlayan kenarlÄ±k Ã§izer.
    base_color deÄŸiÅŸtiÄŸinde otomatik olarak uyum saÄŸlar.
    """
    if w <= 0:
        return

    # Mismatch marker: kutu sÄ±nÄ±rlarÄ±na tam oturan, taÅŸmayan ince outline
    if ann_type == AnnotationType.MISMATCH_MARKER:
        box_y = y + _MM_V_PAD
        box_h = max(1.0, h - 2 * _MM_V_PAD)
        path = _build_repeated_region_path(x, box_y, w, box_h)
        halo_color, inner_color = _selection_colors(base_color)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(Qt.NoBrush)
        halo_pen = QPen(halo_color, 2.5)
        halo_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(halo_pen)
        painter.drawPath(path)
        inner_pen = QPen(inner_color, 1.0)
        inner_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(inner_pen)
        painter.drawPath(path)
        painter.restore()
        return

    if ann_type in (AnnotationType.PRIMER, AnnotationType.PROBE):
        path = _build_primer_probe_path(x, y, w, h, strand, char_width)
    else:
        path = _build_repeated_region_path(x, y, w, h)

    halo_color, inner_color = _selection_colors(base_color)

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setBrush(Qt.NoBrush)
    # DÄ±ÅŸ halo â€” annotation renginden tÃ¼retilmiÅŸ geniÅŸ parlama
    halo_pen = QPen(halo_color, 3.0)
    halo_pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(halo_pen)
    painter.drawPath(path)
    # Ä°Ã§ keskin Ã§izgi â€” kontrast renk
    inner_pen = QPen(inner_color, 1.0)
    inner_pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(inner_pen)
    painter.drawPath(path)
    painter.restore()


def draw_hover_overlay(painter, x, y, w, h, ann_type, base_color,
                       strand="+", char_width=12.0):
    """
    Hover durumunda annotation renginden tÃ¼retilmiÅŸ ince parlaklÄ±k katmanÄ± Ã§izer.
    SeÃ§im state'i aktifken Ã§aÄŸrÄ±lmaz.
    """
    if w <= 0:
        return
    if ann_type in (AnnotationType.PRIMER, AnnotationType.PROBE):
        path = _build_primer_probe_path(x, y, w, h, strand, char_width)
    else:
        path = _build_repeated_region_path(x, y, w, h)

    # Hafif renk aydÄ±nlatma: annotation rengiyle uyumlu hover tonu
    h_f = base_color.hsvHueF()
    s_f = max(0.0, base_color.hsvSaturationF() - 0.1)
    v_f = min(1.0, base_color.valueF() * 0.35 + 0.65)
    overlay = QColor.fromHsvF(h_f if h_f >= 0 else 0.0, s_f, v_f, 0.22)
    border  = QColor.fromHsvF(h_f if h_f >= 0 else 0.0,
                               min(1.0, base_color.hsvSaturationF() + 0.2),
                               min(1.0, base_color.valueF() + 0.15), 0.65)

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    border_pen = QPen(border, 1.3)
    border_pen.setJoinStyle(Qt.RoundJoin)
    painter.setBrush(QBrush(overlay))
    painter.setPen(border_pen)
    painter.drawPath(path)
    painter.restore()


# â”€â”€ Label â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
    # Dikey: tam yÃ¼kseklik â€” descender kÄ±rpÄ±lmasÄ±nÄ± Ã¶nler; hizalama AlignVCenter Ã¼stlenir
    # Yatay: _LABEL_MARGIN ile iÃ§ boÅŸluk
    text_rect = QRectF(x + _LABEL_MARGIN, y, w - _LABEL_MARGIN * 2, h)
    elided = metrics.elidedText(label, Qt.ElideRight, int(text_rect.width()))
    painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignHCenter, elided)


