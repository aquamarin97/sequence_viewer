# features/consensus_row/consensus_row_widget.py
"""
MODIFIED:
- init_state: gizli (is_aligned==False iken). is_aligned==True olunca görünür.
- alignmentStateChanged sinyaline bağlı.
"""
from __future__ import annotations
import math
from typing import Optional, Tuple
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QScrollBar
from features.annotation_layer.annotation_painter import (
    draw_primer, draw_probe, draw_repeated_region,
    draw_hover_overlay, draw_selection_outline,
)
from features.consensus_row.consensus_row_model import ConsensusRowModel
from model.annotation import AnnotationType
from graphics.sequence_item.sequence_glyph_cache import GLYPH_CACHE
from model.alignment_data_model import AlignmentDataModel
from model.consensus_calculator import ConsensusMethod
from settings.theme import theme_manager
from settings.mouse_binding_manager import mouse_binding_manager, MouseAction
from settings.display_settings_manager import display_settings_manager


def _paint_dim_overlay(painter, sequence_viewer, cw, widget_w, widget_h, t):
    """Seçim dışı sütunlar üzerine solduklaştırma katmanı çizer."""
    dim_range = getattr(sequence_viewer, '_selection_dim_range', None)
    if dim_range is None or cw <= 0:
        return
    left_col, right_col = dim_range
    offset = float(sequence_viewer.horizontalScrollBar().value())
    dim_color = QColor(t.selection_dim_color)
    left_px = left_col * cw - offset
    right_px = right_col * cw - offset
    painter.setPen(Qt.NoPen)
    if left_px > 0:
        painter.fillRect(QRectF(0.0, 0.0, min(left_px, widget_w), widget_h), dim_color)
    if right_px < widget_w:
        r = max(right_px, 0.0)
        painter.fillRect(QRectF(r, 0.0, widget_w - r, widget_h), dim_color)


class ConsensusRowWidget(QWidget):
    def __init__(self, alignment_model, sequence_viewer, parent=None):
        super().__init__(parent)
        self._alignment_model = alignment_model
        self._sequence_viewer = sequence_viewer
        self._model = ConsensusRowModel(method=ConsensusMethod.PLURALITY)
        self._font = QFont(display_settings_manager.consensus_font_family)
        self._font.setStyleHint(QFont.Monospace); self._font.setFixedPitch(True)
        from settings.color_styles import color_style_manager as _csm
        self._color_map = _csm.consensus_nucleotide_color_map()
        self._selection = None; self._press_col = None; self._is_selected = False
        self._press_pos = None; self._drag_started = False; self._press_scene_col = None
        self._hit_rects: list = []
        self._press_on_annotation = False
        self._hovered_ann_id: str | None = None
        self._selected_ann_ids: set = set()
        ch = int(round(sequence_viewer.char_height))
        self.setFixedHeight(ch)
        self.setMinimumWidth(0); self.setMouseTracking(True); self.setFocusPolicy(Qt.ClickFocus)
        self.setCursor(Qt.IBeamCursor)

        self._alignment_model.rowAppended.connect(self._on_data_changed)
        self._alignment_model.rowRemoved.connect(self._on_data_changed)
        self._alignment_model.rowMoved.connect(self._on_data_changed)
        self._alignment_model.modelReset.connect(self._on_data_changed)
        self._alignment_model.globalAnnotationAdded.connect(lambda _: self._update_visibility())
        self._alignment_model.globalAnnotationRemoved.connect(lambda _: self._update_visibility())
        self._alignment_model.globalAnnotationUpdated.connect(lambda _: self._update_visibility())
        self._alignment_model.consensusAnnotationAdded.connect(lambda _: self._update_visibility())
        self._alignment_model.consensusAnnotationRemoved.connect(lambda _: self._update_visibility())
        self._alignment_model.consensusAnnotationUpdated.connect(lambda _: self._update_visibility())
        # is_aligned durumuna göre görünürlüğü güncelle
        self._alignment_model.alignmentStateChanged.connect(self._on_alignment_changed)

        hbar = self._sequence_viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self.update); hbar.rangeChanged.connect(self.update)
        anim = getattr(self._sequence_viewer, "_zoom_animation", None)
        if anim: anim.valueChanged.connect(self.update)
        if hasattr(sequence_viewer, 'add_v_guide_observer'):
            sequence_viewer.add_v_guide_observer(self.update)
        theme_manager.themeChanged.connect(lambda _: self._on_theme_changed())
        display_settings_manager.displaySettingsChanged.connect(self._on_display_settings_changed)
        try:
            from settings.color_styles import color_style_manager as _csm2
            _csm2.stylesChanged.connect(self._on_color_styles_changed)
        except: pass
        try:
            from settings.annotation_styles import annotation_style_manager as _asm2
            _asm2.stylesChanged.connect(self._update_visibility)
        except: pass

        # Başlangıçta gizli
        self._update_visibility()

    def _compute_heights(self):
        """Üst annotation, dizi ve alt annotation yüksekliklerini hesapla."""
        from widgets.row_layout import strip_height
        from features.annotation_layer.annotation_layout_engine import assign_lanes, lane_count
        ch = int(round(self._sequence_viewer.char_height))
        annotations = list(self._alignment_model.consensus_annotations) if self._alignment_model.is_aligned else []
        above_anns = [a for a in annotations if a.type.is_above_sequence()]
        below_anns = [a for a in annotations if not a.type.is_above_sequence()]
        above_h = strip_height(lane_count(assign_lanes(above_anns)))
        below_h = strip_height(lane_count(assign_lanes(below_anns)))
        return above_h, ch, below_h

    def _update_visibility(self):
        """is_aligned durumuna göre görünürlük ve yüksekliği ayarla."""
        if self._alignment_model.is_aligned:
            above_h, ch, below_h = self._compute_heights()
            total = above_h + ch + below_h
            self.setFixedHeight(total)
            self.setVisible(True)
            # Spacer'ı senkronize et
            self._sync_spacer()
        else:
            self.setFixedHeight(0)
            self.setVisible(False)
            self._sync_spacer()
        self.update()

    def _sync_spacer(self):
        """Sol paneldeki ConsensusSpacerWidget'ı yükseklikle senkronize et."""
        try:
            p = self.parent()
            while p is not None:
                if hasattr(p, 'consensus_spacer'):
                    h = self.height()
                    if h > 0:
                        p.consensus_spacer.setFixedHeight(h)
                        p.consensus_spacer.setVisible(True)
                        above_h, ch, _ = self._compute_heights()
                        p.consensus_spacer.sync_seq_region(float(above_h), float(ch))
                    else:
                        p.consensus_spacer.setFixedHeight(0)
                        p.consensus_spacer.setVisible(False)
                    break
                p = p.parent()
        except: pass

    def _on_alignment_changed(self, is_aligned):
        self._update_visibility()
        if is_aligned:
            self._model.invalidate()
            self.update()

    def set_method(self, method, threshold=None):
        self._model.set_method(method, threshold); self.update()
    @property
    def current_method(self): return self._model.method
    @property
    def current_threshold(self): return self._model.threshold

    def clear_selection(self):
        self._selection = None
        self._is_selected = False
        self._selected_ann_ids.clear()
        self.update()

    def set_selected(self, selected: bool):
        if self._is_selected == selected: return
        self._is_selected = selected; self.update()

    def select_all(self):
        """Tüm konsensüs dizisini seçili hale getirir."""
        consensus = self._get_consensus()
        if consensus:
            self._selection = (0, len(consensus) - 1)
            self._is_selected = True
            self.update()

    def _col_at_x(self, x):
        cw = self._get_char_width()
        if cw <= 0: return None
        col = int((x + self._get_view_left()) / cw)
        consensus = self._get_consensus()
        if consensus is None: return None
        return max(0, min(col, len(consensus) - 1))

    def _get_consensus(self):
        sequences = [seq for _, seq in self._alignment_model.all_rows()]
        if not sequences: return None
        return self._model.get_consensus(sequences)

    def _on_color_styles_changed(self):
        from settings.color_styles import color_style_manager as _csm
        self._color_map = _csm.consensus_nucleotide_color_map()
        self._model.invalidate(); self.update()

    def _on_data_changed(self, *_): self._model.invalidate(); self.update()
    def _on_theme_changed(self): self._on_color_styles_changed()
    def _on_display_settings_changed(self):
        self._font.setFamily(display_settings_manager.consensus_font_family)
        self._update_visibility()
        self.update()

    def _get_char_width(self):
        if hasattr(self._sequence_viewer, "_get_current_char_width"):
            return float(self._sequence_viewer._get_current_char_width())
        return float(self._sequence_viewer.char_width)

    def _get_view_left(self): return float(self._sequence_viewer.horizontalScrollBar().value())

    def _sync_font_from_viewer(self):
        items = getattr(self._sequence_viewer, "sequence_items", None)
        if items:
            size = float(items[0]._model.current_font_size) + 1.0
        else:
            cw = self._get_char_width()
            cw_default = float(getattr(self._sequence_viewer, "char_width", 12.0)) or 12.0
            scale = cw / cw_default
            con_base = display_settings_manager.consensus_font_size_base
            if scale >= 1.8: size = con_base
            elif scale >= 1.2: size = max(1.0, con_base * (10.0 / 12.0))
            elif scale >= 0.7: size = max(1.0, con_base * (8.0 / 12.0))
            else: size = max(1.0, display_settings_manager.consensus_char_height * 0.6 * scale)
        self._font.setPointSizeF(max(1.0, size))

    def _effective_mode(self):
        items = getattr(self._sequence_viewer, "sequence_items", None)
        if items: return items[0]._model.get_effective_mode()
        return "text"

    def _scene_col_at_x(self, vp_x: float) -> int:
        """Viewport x → NA kolonu (tam NA, kesme yok)."""
        cw = self._get_char_width()
        if cw <= 0: return 0
        scene_x = vp_x + self._get_view_left()
        return int(scene_x / cw)

    def _boundary_col_at_x(self, vp_x: float) -> int:
        """Viewport x → en yakın NA sınırı (yarı-yarıya bölünmüş)."""
        cw = self._get_char_width()
        if cw <= 0: return 0
        scene_x = vp_x + self._get_view_left()
        return int(round(scene_x / cw))

    def _get_controller(self):
        ctrl = getattr(self._sequence_viewer, '_controller', None)
        return ctrl

    def _notify_header_cleared(self):
        """Header seçimini temizle, workspace'e bildir — guide'ları etkileme."""
        try:
            p = self.parent()
            while p is not None:
                if hasattr(p, 'consensus_spacer') and hasattr(p, 'header_viewer'):
                    p.consensus_spacer.set_selected(True)
                    changed = p.header_viewer._selection.clear()
                    p.header_viewer.apply_selection_to_items(changed)
                    # on_selection_changed'i ÇAĞIRMA — o clear_v_guides yapar
                    # Sadece h_guides'ı temizle, v_guides'a dokunma
                    p.sequence_viewer.clear_h_guides()
                    for item in p.sequence_viewer.sequence_items:
                        item.clear_selection()
                    p.sequence_viewer.scene.invalidate()
                    p.sequence_viewer.viewport().update()
                    break
                p = p.parent()
        except: pass

    def _notify_edit_annotation(self, ann):
        """Consensus annotation düzenleme diyaloğunu workspace üzerinden aç."""
        try:
            p = self.parent()
            while p is not None:
                if hasattr(p, 'open_edit_consensus_annotation_dialog'):
                    p.open_edit_consensus_annotation_dialog(ann)
                    return
                p = p.parent()
        except Exception:
            pass

    def leaveEvent(self, event):
        if self._hovered_ann_id is not None:
            self._hovered_ann_id = None
            self.setCursor(Qt.IBeamCursor)
            self.update()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            ann = self._annotation_at(event.pos())
            if ann:
                self._notify_edit_annotation(ann)
                event.accept(); return
        super().mouseDoubleClickEvent(event)

    def _select_annotation_range(self, ann, ctrl=False):
        """Annotation aralığını seçili yap ve guide çizgileri oluştur."""
        if ctrl:
            if ann.id in self._selected_ann_ids:
                self._selected_ann_ids.discard(ann.id)
                if not self._selected_ann_ids:
                    self._selection = None
                    self._is_selected = False
            else:
                self._selected_ann_ids.add(ann.id)
                self._selection = (ann.start, ann.end)
                self._is_selected = True
            self.update()
            return
        # Tekil seçim: önceki seçimi temizle, yeni annotation'ı seç
        self._selected_ann_ids = {ann.id}
        self._selection = (ann.start, ann.end)
        self._is_selected = True
        self._sequence_viewer.set_selection_dim_range(ann.start, ann.end + 1)
        self.update()
        # Guide çizgileri: ilk NA'nın solu ve son NA'nın sağı
        c = self._get_controller()
        if c is not None:
            left_b = ann.start
            right_b = ann.end + 1
            c._v_guide_cols = [left_b, right_b]
            self._sequence_viewer.set_v_guides(c._v_guide_cols)

    def _annotation_at(self, pos):
        p = QRectF(pos.x(), pos.y(), 1, 1)
        for rect, ann in self._hit_rects:
            if rect.intersects(p): return ann
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Annotation tıklaması — seçim + guide
            ann = self._annotation_at(event.pos())
            if ann:
                self._press_on_annotation = True
                ctrl = bool(event.modifiers() & Qt.ControlModifier)
                self._select_annotation_range(ann, ctrl=ctrl)
                event.accept(); return
            self._press_on_annotation = False
            self._selected_ann_id = None
            self.setFocus()
            self._sequence_viewer.clear_visual_selection()
            try: self._sequence_viewer._model.clear_selection()
            except: pass
            # Drag threshold için press pozisyonunu sakla
            from PyQt5.QtCore import QPoint
            self._press_pos = QPoint(event.pos())
            self._press_scene_col = self._scene_col_at_x(float(event.pos().x()))
            self._drag_started = False
            self._is_selected = True
            self._notify_header_cleared()
            # Position ruler'ı güncelle
            try:
                p = self.parent()
                while p is not None:
                    if hasattr(p, 'pos_ruler'):
                        p.pos_ruler.update(); break
                    p = p.parent()
            except: pass
            event.accept()
        else: super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is None:
            ann = self._annotation_at(event.pos())
            new_hovered_id = ann.id if ann else None
            if new_hovered_id != self._hovered_ann_id:
                self._hovered_ann_id = new_hovered_id
                self.setCursor(Qt.PointingHandCursor if ann else Qt.IBeamCursor)
                self.update()
            if ann:
                from PyQt5.QtWidgets import QToolTip
                QToolTip.showText(event.globalPos(), ann.tooltip_text(), self)
            else:
                from PyQt5.QtWidgets import QToolTip
                QToolTip.hideText()
            super().mouseMoveEvent(event); return

        delta = (event.pos() - self._press_pos).manhattanLength()

        if not self._drag_started and delta >= mouse_binding_manager.drag_threshold("consensus_row"):
            self._drag_started = True
            drag_action = mouse_binding_manager.resolve_sequence_drag(event.modifiers())
            c = self._get_controller()
            if drag_action == MouseAction.DRAG_SELECT and c is not None:
                c._v_guide_cols.clear()
                self._sequence_viewer.set_v_guides(c._v_guide_cols)
            self.setCursor(Qt.SizeHorCursor)
            # Drag başladığı anda başlangıç kolonu için guide'ı hemen göster
            if c is not None and self._press_scene_col is not None:
                col = self._scene_col_at_x(float(event.pos().x()))
                lo, hi = min(self._press_scene_col, col), max(self._press_scene_col, col)
                if hi > lo:
                    self._selection = (lo, hi)
                    left_b, right_b = lo, hi + 1
                    c._v_guide_cols = [left_b, right_b]
                    self._sequence_viewer.set_v_guides(c._v_guide_cols)
                    self.update()

        if self._drag_started:
            col = self._scene_col_at_x(float(event.pos().x()))
            start = self._press_scene_col
            if start is not None:
                lo, hi = min(start, col), max(start, col)
                c = self._get_controller()
                if hi > lo:
                    self._selection = (lo, hi)
                    if c is not None:
                        left_b, right_b = lo, hi + 1
                        # Drag aktifken sadece bu ikisini göster — önceki drag değerlerini biriktirme
                        c._v_guide_cols = [left_b, right_b]
                        self._sequence_viewer.set_v_guides(c._v_guide_cols)
                else:
                    self._selection = None
                    if c is not None:
                        self._sequence_viewer.set_v_guides(c._v_guide_cols)
                self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.unsetCursor()
            self.setCursor(Qt.IBeamCursor)

            if self._drag_started:
                # Drag bitti — guide'ları kalıcı hale getir
                self._drag_started = False
                self._press_pos = None
                c = self._get_controller()
                if c is not None and self._selection is not None:
                    lo, hi = self._selection
                    if hi > lo:
                        drag_action = mouse_binding_manager.resolve_sequence_drag(event.modifiers())
                        if drag_action == MouseAction.DRAG_SELECT:
                            c._v_guide_cols.clear()
                        for b in (lo, hi + 1):
                            if b not in c._v_guide_cols:
                                c._v_guide_cols.append(b)
                        self._sequence_viewer.set_v_guides(c._v_guide_cols)
            else:
                self._press_pos = None
                self._drag_started = False
                if self._press_on_annotation:
                    # Annotation click'i: selection press'te set edildi, temizleme
                    self._press_on_annotation = False
                    self.update()
                    event.accept()
                    return
                # Drag yok → boundary tıklama → guide
                self._selection = None
                boundary_col = self._boundary_col_at_x(float(event.pos().x()))
                c = self._get_controller()
                if c is not None:
                    click_action = mouse_binding_manager.resolve_sequence_click(event.modifiers())
                    if click_action == MouseAction.GUIDE_TOGGLE:
                        if boundary_col in c._v_guide_cols:
                            c._v_guide_cols.remove(boundary_col)
                        else:
                            c._v_guide_cols.append(boundary_col)
                    else:
                        c._v_guide_cols = [boundary_col]
                    self._sequence_viewer.set_v_guides(c._v_guide_cols)

            self.update()
            event.accept()
        else: super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        if event.key() == Qt.Key_Delete and self._selected_ann_id is not None:
            self._delete_selected_annotation(); event.accept()
        elif ctrl and shift and event.key() == Qt.Key_C:
            self._copy_fasta(); event.accept()
        elif ctrl and not shift and event.key() == Qt.Key_C:
            self._copy_sequence(); event.accept()
        else:
            super().keyPressEvent(event)

    def _delete_selected_annotation(self):
        ann_ids = set(self._selected_ann_ids)
        self._selected_ann_ids.clear()
        self._selection = None
        self._is_selected = False
        self.update()
        for ann_id in ann_ids:
            try:
                self._alignment_model.remove_consensus_annotation(ann_id)
            except (KeyError, Exception):
                pass

    def _copy_sequence(self):
        consensus = self._get_consensus()
        if not consensus: return
        if self._selection is not None:
            col_start, col_end = self._selection
            fragment = consensus[col_start:col_end + 1]
        else:
            fragment = consensus
        QApplication.clipboard().setText(fragment)

    def _copy_fasta(self):
        consensus = self._get_consensus()
        if not consensus: return
        label = "Consensus"
        try:
            p = self.parent()
            while p is not None:
                if hasattr(p, 'consensus_spacer'):
                    label = p.consensus_spacer.label; break
                p = p.parent()
        except: pass
        if self._selection is not None:
            col_start, col_end = self._selection
            seq = consensus[col_start:col_end + 1]
        else:
            seq = consensus
        QApplication.clipboard().setText(f">{label}\n{seq}")

    def paintEvent(self, event):
        if not self.isVisible() or self.height() == 0: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        rect = self.rect(); width = rect.width(); height = rect.height()
        t = theme_manager.current
        # Seçim vurgusu: seçiliyse row_band_highlight, değilse row_bg_odd
        is_selected = self._is_selected
        bg_color = QColor(t.row_band_highlight) if is_selected else t.row_bg_odd
        painter.fillRect(rect, QBrush(bg_color))
        # Sol kenar çizgisi (seçili iken)
        if is_selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(t.drop_indicator))
            painter.drawRect(0, 0, 2, height)
        painter.setPen(QPen(t.border_normal)); painter.drawLine(0, height-1, width, height-1)
        sequences = [seq for _, seq in self._alignment_model.all_rows()]
        _char_h = float(int(round(self._sequence_viewer.char_height)))
        if not sequences:
            label_font = QFont("Arial")
            label_font.setPointSizeF(max(1.0, _char_h * 0.5))
            painter.setPen(QPen(t.text_primary)); painter.setFont(label_font)
            painter.drawText(rect.adjusted(6,0,0,0), Qt.AlignVCenter|Qt.AlignLeft, "—")
            painter.end(); return
        consensus = self._model.get_consensus(sequences)
        if not consensus: painter.end(); return
        cw = self._get_char_width(); view_left = self._get_view_left()
        if cw <= 0: painter.end(); return
        self._sync_font_from_viewer(); painter.setFont(self._font)
        mode = self._effective_mode()
        # Annotation lane yüksekliklerini hesapla
        from widgets.row_layout import strip_height
        from features.annotation_layer.annotation_layout_engine import assign_lanes, lane_count
        _anns = list(self._alignment_model.consensus_annotations) if self._alignment_model.is_aligned else []
        _above_anns = [a for a in _anns if a.type.is_above_sequence()]
        _above_h = float(strip_height(lane_count(assign_lanes(_above_anns))))
        seq_char_h = float(int(round(self._sequence_viewer.char_height)))
        seq_top = _above_h  # dizi bu y'den başlar
        length = len(consensus)
        start_col = max(0, int(math.floor(view_left / cw)))
        end_col = min(length, int(math.ceil((view_left + width) / cw)))
        sel_start = sel_end = None
        if self._selection: sel_start, sel_end = self._selection
        ch = seq_char_h  # dizi satırının yüksekliği
        if mode == "line":
            line_h = ch * 0.3; y = seq_top + (ch - line_h) / 2.0
            x_start = max(0.0, start_col * cw - view_left)
            x_end = min(end_col * cw - view_left, float(width))
            draw_width = max(0.0, x_end - x_start)
            painter.setBrush(QBrush(t.seq_line_fg)); painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(x_start, y, draw_width, line_h))
            if sel_start is not None and sel_end is not None:
                sx = sel_start * cw - view_left; sw = (sel_end - sel_start + 1) * cw
                sx2 = max(0.0, sx); sw2 = min(sw - (sx2 - sx), float(width) - sx2)
                if sw2 > 0:
                    sel_color = QColor(t.seq_selection_bg)
                    painter.setBrush(QBrush(sel_color)); painter.drawRect(QRectF(sx2, seq_top, sw2, ch))
            _paint_dim_overlay(painter, self._sequence_viewer, cw, float(width), float(height), t)
            painter.end(); return
        if sel_start is not None and sel_end is not None:
            sel_l = max(sel_start, start_col); sel_r = min(sel_end + 1, end_col)
            if sel_r > sel_l:
                sel_color = QColor(t.seq_selection_bg)
                painter.setBrush(QBrush(sel_color)); painter.setPen(Qt.NoPen)
                for i in range(sel_l, sel_r):
                    painter.drawRect(QRectF(i * cw - view_left, seq_top, cw, ch))
        font_pt = self._font.pointSizeF()
        box_ref = min(ch * 0.7, font_pt); box_h = max(box_ref, 1.0); box_y = seq_top + (ch - box_h) / 2.0
        for col in range(start_col, end_col):
            base = consensus[col].upper(); x = col * cw - view_left
            is_selected = sel_start is not None and sel_end is not None and sel_start <= col <= sel_end
            color = QColor(255, 255, 255) if is_selected else self._color_map.get(base, t.text_primary)
            if mode == "box":
                painter.setBrush(QBrush(color)); painter.setPen(Qt.NoPen)
                painter.drawRect(QRectF(x, box_y, cw, box_h))
            else:
                glyph = GLYPH_CACHE.get_glyph(base, self._font, color)
                dx = x + (cw - glyph.width()) / 2.0; dy = seq_top + (ch - glyph.height()) / 2.0
                painter.drawPixmap(int(dx), int(dy), glyph)

        # ---- Annotation overlay ----
        self._hit_rects = []
        annotations = list(self._alignment_model.consensus_annotations) if self._alignment_model.is_aligned else []
        if annotations:
            from widgets.row_layout import above_lane_y, below_lane_y, strip_height
            from features.annotation_layer.annotation_layout_engine import assign_lanes, lane_count
            from settings.annotation_styles import annotation_style_manager as _asm_cr
            _LANE_H = _asm_cr.get_lane_height()
            above_anns = [a for a in annotations if a.type.is_above_sequence()]
            below_anns = [a for a in annotations if not a.type.is_above_sequence()]
            above_assignment = assign_lanes(above_anns)
            below_assignment = assign_lanes(below_anns)
            above_h = strip_height(lane_count(above_assignment))
            # dizi alanı above_h'den başlar
            seq_top = float(above_h)
            painter.setRenderHint(QPainter.Antialiasing, True)
            widget_w = float(width)
            for ann in annotations:
                x = ann.start * cw - view_left
                w_ann = ann.length() * cw
                if x + w_ann < 0 or x > widget_w: continue
                clipped_x = max(x, 0.0)
                clipped_w = min(w_ann - (clipped_x - x), widget_w - clipped_x)
                if clipped_w <= 0: continue
                ann_char_w = clipped_w / max(ann.length(), 1)
                if ann.type.is_above_sequence():
                    lane = above_assignment.get(ann.id, 0)
                    ann_y = above_lane_y(lane)
                else:
                    lane = below_assignment.get(ann.id, 0)
                    ann_y = seq_top + ch + below_lane_y(lane)
                ann_h_draw = _LANE_H
                ann_color = ann.resolved_color()
                ann_strand = getattr(ann, 'strand', '+')
                painter.save()
                if ann.type == AnnotationType.PRIMER:
                    draw_primer(painter, clipped_x, ann_y, clipped_w, ann_h_draw, ann_color, ann.label, strand=ann_strand, char_width=ann_char_w)
                elif ann.type == AnnotationType.PROBE:
                    draw_probe(painter, clipped_x, ann_y, clipped_w, ann_h_draw, ann_color, ann.label, strand=ann_strand, char_width=ann_char_w)
                else:
                    draw_repeated_region(painter, clipped_x, ann_y, clipped_w, ann_h_draw, ann_color, ann.label)
                is_ann_selected = ann.id in self._selected_ann_ids
                is_ann_hovered  = (ann.id == self._hovered_ann_id)
                if is_ann_hovered and not is_ann_selected:
                    draw_hover_overlay(painter, clipped_x, ann_y, clipped_w, ann_h_draw,
                                       ann.type, ann_color, strand=ann_strand, char_width=ann_char_w)
                if is_ann_selected:
                    draw_selection_outline(painter, clipped_x, ann_y, clipped_w, ann_h_draw,
                                           ann.type, ann_color, strand=ann_strand, char_width=ann_char_w)
                painter.restore()
                self._hit_rects.append((QRectF(clipped_x, ann_y, clipped_w, ann_h_draw), ann))
            painter.setRenderHint(QPainter.Antialiasing, False)

        # ---- Seçim odak efekti ----
        _paint_dim_overlay(painter, self._sequence_viewer, cw, float(width), float(height), t)

        # ---- Dikey kılavuz çizgileri ----
        ctrl = self._get_controller()
        if ctrl is not None and ctrl._v_guide_cols:
            hbar = self._sequence_viewer.horizontalScrollBar()
            offset = float(hbar.value())
            vp_w = float(self.width())
            pen = QPen(theme_manager.current.guide_line_color, 1, Qt.DashLine)
            pen.setDashPattern([4, 3]); painter.setPen(pen)
            for gcol in ctrl._v_guide_cols:
                vp_x = gcol * cw - offset
                if -10 <= vp_x <= vp_w + 10:
                    painter.drawLine(QPointF(vp_x, 0), QPointF(vp_x, float(height)))

        painter.end()