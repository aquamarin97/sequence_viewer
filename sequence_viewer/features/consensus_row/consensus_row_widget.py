# features/consensus_row/consensus_row_widget.py
"""
MODIFIED:
- init_state: gizli (is_aligned==False iken). is_aligned==True olunca gÃ¶rÃ¼nÃ¼r.
- alignmentStateChanged sinyaline baÄŸlÄ±.
"""
from __future__ import annotations
import math
from typing import Optional, Tuple
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QScrollBar
from sequence_viewer.features.annotation_layer.annotation_painter import (
    draw_primer, draw_probe, draw_repeated_region,
    draw_hover_overlay, draw_selection_outline, draw_mismatch_marker,
)
from sequence_viewer.features.annotation_layer.annotation_layout_engine import build_side_geometry, partition_annotations_by_side, side_strip_height
from sequence_viewer.features.consensus_row.consensus_row_model import ConsensusRowModel
from sequence_viewer.model.annotation import AnnotationType
from sequence_viewer.graphics.sequence_item.sequence_glyph_cache import GLYPH_CACHE
from sequence_viewer.model.alignment_data_model import AlignmentDataModel
from sequence_viewer.model.consensus_calculator import ConsensusMethod
from sequence_viewer.settings.theme import theme_manager
from sequence_viewer.settings.mouse_binding_manager import mouse_binding_manager, MouseAction
from sequence_viewer.settings.display_settings_manager import display_settings_manager
from sequence_viewer.utils.drag_tooltip import DragTooltip
from sequence_viewer.utils.sequence_utils import selection_bp, calculate_tm


def _paint_dim_overlay(painter, sequence_viewer, cw, widget_w, widget_h, t):
    """SeÃ§im dÄ±ÅŸÄ± sÃ¼tunlar Ã¼zerine solduklaÅŸtÄ±rma katmanÄ± Ã§izer (Ã§oklu focus aralÄ±ÄŸÄ± destekli)."""
    dim_ranges = getattr(sequence_viewer, '_selection_dim_ranges', None)
    if not dim_ranges or cw <= 0:
        return
    offset = float(sequence_viewer.horizontalScrollBar().value())
    dim_color = QColor(t.selection_dim_color)
    sorted_ranges = sorted(dim_ranges, key=lambda r: r[0])
    painter.setPen(Qt.NoPen)
    prev_right_px = 0.0
    for left_col, right_col in sorted_ranges:
        left_px = left_col * cw - offset
        right_px = right_col * cw - offset
        if left_px > prev_right_px:
            x = max(prev_right_px, 0.0)
            w = min(left_px, widget_w) - x
            if w > 0:
                painter.fillRect(QRectF(x, 0.0, w, widget_h), dim_color)
        prev_right_px = max(prev_right_px, right_px)
    if prev_right_px < widget_w:
        r = max(prev_right_px, 0.0)
        painter.fillRect(QRectF(r, 0.0, widget_w - r, widget_h), dim_color)


class ConsensusRowWidget(QWidget):
    def __init__(self, alignment_model, sequence_viewer, parent=None):
        super().__init__(parent)
        self._alignment_model = alignment_model
        self._sequence_viewer = sequence_viewer
        self._model = ConsensusRowModel(method=ConsensusMethod.PLURALITY)
        self._font = QFont(display_settings_manager.consensus_font_family)
        self._font.setStyleHint(QFont.Monospace); self._font.setFixedPitch(True)
        from sequence_viewer.settings.color_styles import color_style_manager as _csm
        self._color_map = _csm.consensus_nucleotide_color_map()
        self._press_col = None; self._is_selected = False
        self._press_pos = None; self._drag_started = False; self._press_scene_col = None
        self._drag_tooltip = DragTooltip()
        self._hit_rects: list = []
        self._press_on_annotation = False
        self._hovered_ann_id: str | None = None
        self._selected_ann_ids: set = set()
        self._selection_ranges: list = []   # [(start_incl, end_excl), ...] â€” multi-range
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
        # is_aligned durumuna gÃ¶re gÃ¶rÃ¼nÃ¼rlÃ¼ÄŸÃ¼ gÃ¼ncelle
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
            from sequence_viewer.settings.color_styles import color_style_manager as _csm2
            _csm2.stylesChanged.connect(self._on_color_styles_changed)
        except: pass
        try:
            from sequence_viewer.settings.annotation_styles import annotation_style_manager as _asm2
            _asm2.stylesChanged.connect(self._update_visibility)
        except: pass

        # BaÅŸlangÄ±Ã§ta gizli
        self._update_visibility()

    def _compute_heights(self):
        """Ãœst annotation, dizi ve alt annotation yÃ¼ksekliklerini hesapla."""
        ch = int(round(self._sequence_viewer.char_height))
        annotations = list(self._alignment_model.consensus_annotations) if self._alignment_model.is_aligned else []
        above_anns, below_anns = partition_annotations_by_side(annotations)
        above_h = side_strip_height(above_anns)
        below_h = side_strip_height(below_anns)
        return above_h, ch, below_h

    def _update_visibility(self):
        """is_aligned durumuna gÃ¶re gÃ¶rÃ¼nÃ¼rlÃ¼k ve yÃ¼ksekliÄŸi ayarla."""
        if self._alignment_model.is_aligned:
            above_h, ch, below_h = self._compute_heights()
            total = above_h + ch + below_h
            self.setFixedHeight(total)
            self.setVisible(True)
            # Spacer'Ä± senkronize et
            self._sync_spacer()
        else:
            self.setFixedHeight(0)
            self.setVisible(False)
            self._sync_spacer()
        self.update()

    def _sync_spacer(self):
        """Sol paneldeki ConsensusSpacerWidget'Ä± yÃ¼kseklikle senkronize et."""
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

    # ------------------------------------------------------------------
    # _selection: drag ve tekli annotation seÃ§imi iÃ§in backward-compat property
    # backing store: _selection_ranges [(start_incl, end_excl), ...]
    # ------------------------------------------------------------------
    @property
    def _selection(self):
        """Ä°lk aralÄ±ÄŸÄ± (start_incl, end_incl) olarak dÃ¶ndÃ¼rÃ¼r; yoksa None."""
        if self._selection_ranges:
            s, e = self._selection_ranges[0]
            return (s, e - 1)
        return None

    @_selection.setter
    def _selection(self, value):
        if value is None:
            self._selection_ranges = []
        else:
            s, e = value  # end inclusive
            self._selection_ranges = [(s, e + 1)]

    def clear_selection(self):
        self._selection_ranges = []
        self._is_selected = False
        self._selected_ann_ids.clear()
        self._notify_spacer_selected(False)
        self.update()

    def set_selected(self, selected: bool):
        if self._is_selected == selected: return
        self._is_selected = selected; self.update()

    def select_all(self):
        """TÃ¼m konsensÃ¼s dizisini seÃ§ili hale getirir."""
        consensus = self._get_consensus()
        if consensus:
            self._selection_ranges = [(0, len(consensus))]
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
        from sequence_viewer.settings.color_styles import color_style_manager as _csm
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
        """Viewport x â†’ NA kolonu (tam NA, kesme yok)."""
        cw = self._get_char_width()
        if cw <= 0: return 0
        scene_x = vp_x + self._get_view_left()
        return int(scene_x / cw)

    def _boundary_col_at_x(self, vp_x: float) -> int:
        """Viewport x â†’ en yakÄ±n NA sÄ±nÄ±rÄ± (yarÄ±-yarÄ±ya bÃ¶lÃ¼nmÃ¼ÅŸ)."""
        cw = self._get_char_width()
        if cw <= 0: return 0
        scene_x = vp_x + self._get_view_left()
        return int(round(scene_x / cw))

    def _get_controller(self):
        ctrl = getattr(self._sequence_viewer, '_controller', None)
        return ctrl

    def _notify_header_cleared(self):
        """Header seÃ§imini temizle, workspace'e bildir â€” guide'larÄ± etkileme."""
        try:
            p = self.parent()
            while p is not None:
                if hasattr(p, 'consensus_spacer') and hasattr(p, 'header_viewer'):
                    p.consensus_spacer.set_selected(True)
                    changed = p.header_viewer._selection.clear()
                    p.header_viewer.apply_selection_to_items(changed)
                    # on_selection_changed'i Ã‡AÄIRMA â€” o clear_v_guides yapar
                    # Sadece h_guides'Ä± temizle, v_guides'a dokunma
                    p.sequence_viewer.clear_h_guides()
                    for item in p.sequence_viewer.sequence_items:
                        item.clear_selection()
                    p.sequence_viewer.scene.invalidate()
                    p.sequence_viewer.viewport().update()
                    break
                p = p.parent()
        except: pass

    def _notify_edit_annotation(self, ann):
        """Consensus annotation dÃ¼zenleme diyaloÄŸunu workspace Ã¼zerinden aÃ§."""
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

    # ------------------------------------------------------------------
    # Drag tooltip
    # ------------------------------------------------------------------
    def _update_drag_tooltip(self, event) -> None:
        """Show / update the floating Bp/Tm panel near the cursor."""
        sel = self._selection   # (start_incl, end_incl) or None
        if sel is None:
            self._drag_tooltip.clear_tooltip()
            return
        lo, hi = sel
        if hi <= lo:
            self._drag_tooltip.clear_tooltip()
            return
        bp = selection_bp(lo, hi)
        consensus = self._get_consensus()
        tm = calculate_tm(consensus[lo:hi + 1]) if consensus else None
        global_pos = self.mapToGlobal(event.pos())
        self._drag_tooltip.show_bp_tm(global_pos, bp, tm)

    def mouseDoubleClickEvent(self, event):
        if mouse_binding_manager.is_annotation_edit_event(event.modifiers(), event.button()):
            ann = self._annotation_at(event.pos())
            if ann and ann.type != AnnotationType.MISMATCH_MARKER:
                self._notify_edit_annotation(ann)
                event.accept(); return
            if ann:
                event.accept(); return
        super().mouseDoubleClickEvent(event)

    def _notify_workspace_ann_cleared(self):
        """Workspace coordinator'Ä±n annotation seÃ§imini temizle (koordinasyon)."""
        try:
            p = self.parent()
            while p is not None:
                if hasattr(p, '_action_dialogs'):
                    ad = p._action_dialogs
                    if ad._selected_annotations:
                        ad._selected_annotations.clear()
                        ad._clear_all_annotation_visuals()
                    break
                p = p.parent()
        except Exception:
            pass

    def _notify_spacer_selected(self, selected: bool):
        """Sol paneldeki consensus_spacer'Ä± seÃ§im durumuna gÃ¶re gÃ¼ncelle."""
        try:
            p = self.parent()
            while p is not None:
                if hasattr(p, 'consensus_spacer'):
                    p.consensus_spacer.set_selected(selected)
                    break
                p = p.parent()
        except Exception:
            pass

    def _notify_coordinator_refresh(self):
        """Coordinator'Ä±n _apply_union_selection'Ä±nÄ± tetikle (cross-widget merge)."""
        try:
            p = self.parent()
            while p is not None:
                if hasattr(p, '_action_dialogs'):
                    p._action_dialogs._apply_union_selection()
                    break
                p = p.parent()
        except Exception:
            pass

    def _select_annotation_range(self, ann, ctrl=False):
        """Annotation aralÄ±ÄŸÄ±nÄ± seÃ§ili yap ve guide Ã§izgileri oluÅŸtur."""
        c = self._get_controller()

        if ctrl:
            # Additive: coordinator seÃ§imini KORU, sadece kendi state'ini gÃ¼ncelle
            if ann.id in self._selected_ann_ids:
                self._selected_ann_ids.discard(ann.id)
            else:
                self._selected_ann_ids.add(ann.id)
            self._is_selected = bool(self._selected_ann_ids)
            self._notify_spacer_selected(self._is_selected)
            # SeÃ§ili annotation nesnelerini bul ve _selection_ranges'i gÃ¼ncelle
            ann_map = {a.id: a for a in (
                self._alignment_model.consensus_annotations
                if self._alignment_model.is_aligned else [])}
            selected_anns = [ann_map[aid] for aid in self._selected_ann_ids if aid in ann_map]
            if selected_anns:
                self._selection_ranges = [
                    (a.start, a.start + 1) if a.type == AnnotationType.MISMATCH_MARKER else (a.start, a.end + 1)
                    for a in selected_anns
                ]
            else:
                self._selection_ranges = []
            self.update()
            # Coordinator'a merge refresh bildir â€” guides + dim + seq selection hesaplar
            self._notify_coordinator_refresh()
            return

        # Tekil seÃ§im: coordinator'Ä± temizle, kendi seÃ§imini yap
        self._notify_workspace_ann_cleared()
        self._selected_ann_ids = {ann.id}
        self._selection_ranges = [(ann.start, ann.start + 1) if ann.type == AnnotationType.MISMATCH_MARKER else (ann.start, ann.end + 1)]
        self._is_selected = True
        self._notify_spacer_selected(True)
        # Controller Ã–NCE gÃ¼ncelle â€” observers paint sÄ±rasÄ±nda okur
        if c is not None:
            c._v_guide_cols = [ann.start] if ann.type == AnnotationType.MISMATCH_MARKER else [ann.start, ann.end + 1]
        self._sequence_viewer.set_v_guides([ann.start] if ann.type == AnnotationType.MISMATCH_MARKER else [ann.start, ann.end + 1])
        self._sequence_viewer.set_selection_dim_range(ann.start, ann.start + 1 if ann.type == AnnotationType.MISMATCH_MARKER else ann.end + 1)
        self.update()

    def _annotation_at(self, pos):
        p = QRectF(pos.x(), pos.y(), 1, 1)
        for rect, ann in self._hit_rects:
            if rect.intersects(p): return ann
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Annotation tÄ±klamasÄ± â€” seÃ§im + guide
            ann = self._annotation_at(event.pos())
            if ann:
                self._press_on_annotation = True
                self._sequence_viewer.clear_caret()
                action = mouse_binding_manager.resolve_annotation_click(event.modifiers(), event.button())
                if action == MouseAction.NONE:
                    super().mousePressEvent(event)
                    return
                self._select_annotation_range(ann, ctrl=(action == MouseAction.ANNOTATION_MULTI_SELECT))
                event.accept(); return
            self._press_on_annotation = False
            self._selected_ann_ids.clear()
            self._notify_workspace_ann_cleared()
            # Annotation seÃ§iminin bÄ±raktÄ±ÄŸÄ± dim + v_guide'larÄ± temizle
            self._sequence_viewer.clear_selection_dim_range()
            c = self._get_controller()
            if c is not None:
                c._v_guide_cols = []
            self._sequence_viewer.set_v_guides([])
            self.update()
            self.setFocus()
            self._sequence_viewer.clear_visual_selection()
            try: self._sequence_viewer._model.clear_selection()
            except: pass
            # Drag threshold iÃ§in press pozisyonunu sakla
            from PyQt5.QtCore import QPoint
            self._press_pos = QPoint(event.pos())
            self._press_scene_col = self._scene_col_at_x(float(event.pos().x()))
            self._drag_started = False
            self._is_selected = True
            self._notify_header_cleared()
            # Position ruler'Ä± gÃ¼ncelle
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
            drag_action = mouse_binding_manager.resolve_sequence_drag(event.modifiers(), Qt.LeftButton)
            if drag_action == MouseAction.NONE:
                super().mouseMoveEvent(event)
                return
            self._drag_started = True
            c = self._get_controller()
            if drag_action == MouseAction.DRAG_SELECT and c is not None:
                c._v_guide_cols.clear()
                self._sequence_viewer.set_v_guides(c._v_guide_cols)
            self._sequence_viewer.clear_caret()
            self.setCursor(Qt.SizeHorCursor)
            # Drag baÅŸladÄ±ÄŸÄ± anda baÅŸlangÄ±Ã§ kolonu iÃ§in guide'Ä± hemen gÃ¶ster
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
                        # Drag aktifken sadece bu ikisini gÃ¶ster â€” Ã¶nceki drag deÄŸerlerini biriktirme
                        c._v_guide_cols = [left_b, right_b]
                        self._sequence_viewer.set_v_guides(c._v_guide_cols)
                else:
                    self._selection = None
                    if c is not None:
                        self._sequence_viewer.set_v_guides(c._v_guide_cols)
                self._update_drag_tooltip(event)
                self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.unsetCursor()
            self.setCursor(Qt.IBeamCursor)

            if self._drag_started:
                self._drag_tooltip.clear_tooltip()
                # Drag bitti â€” guide'larÄ± kalÄ±cÄ± hale getir
                self._drag_started = False
                self._press_pos = None
                c = self._get_controller()
                if c is not None and self._selection is not None:
                    lo, hi = self._selection
                    if hi > lo:
                        drag_action = mouse_binding_manager.resolve_sequence_drag(event.modifiers(), Qt.LeftButton)
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
                # Drag yok â†’ boundary tÄ±klama â†’ guide
                self._selection = None
                boundary_col = self._boundary_col_at_x(float(event.pos().x()))
                c = self._get_controller()
                if c is not None:
                    click_action = mouse_binding_manager.resolve_sequence_click(event.modifiers(), Qt.LeftButton)
                    if click_action == MouseAction.NONE:
                        self.update()
                        event.accept()
                        return
                    if click_action == MouseAction.GUIDE_TOGGLE:
                        if boundary_col in c._v_guide_cols:
                            c._v_guide_cols.remove(boundary_col)
                        else:
                            c._v_guide_cols.append(boundary_col)
                    else:
                        c._v_guide_cols = [boundary_col]
                        self._sequence_viewer.set_caret(boundary_col, -1)
                    self._sequence_viewer.set_v_guides(c._v_guide_cols)

            self.update()
            event.accept()
        else: super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        if event.key() == Qt.Key_Delete and self._selected_ann_ids:
            self.delete_selected_annotations(); event.accept()
        elif ctrl and shift and event.key() == Qt.Key_C:
            self._copy_fasta(); event.accept()
        elif ctrl and not shift and event.key() == Qt.Key_C:
            self._copy_sequence(); event.accept()
        else:
            super().keyPressEvent(event)

    def delete_selected_annotations(self):
        ann_ids = set(self._selected_ann_ids)
        if not ann_ids:
            return
        try:
            p = self.parent()
            while p is not None:
                if hasattr(p, 'delete_consensus_annotations_with_undo'):
                    p.delete_consensus_annotations_with_undo(ann_ids)
                    return
                p = p.parent()
        except Exception:
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
        # SeÃ§im vurgusu: seÃ§iliyse row_band_highlight, deÄŸilse row_bg_odd
        is_selected = self._is_selected
        bg_color = QColor(t.row_band_highlight) if is_selected else t.row_bg_odd
        painter.fillRect(rect, QBrush(bg_color))
        painter.setPen(QPen(t.border_normal)); painter.drawLine(0, height-1, width, height-1)
        # Yatay kÄ±lavuz Ã§izgileri: dizi seÃ§iliyken ve annotation seÃ§imi yokken
        if is_selected and not self._selected_ann_ids:
            h_pen = QPen(t.guide_line_color, 1, Qt.SolidLine)
            painter.setPen(h_pen)
            painter.drawLine(0, height - 1, width, height - 1)
        sequences = [seq for _, seq in self._alignment_model.all_rows()]
        _char_h = float(int(round(self._sequence_viewer.char_height)))
        if not sequences:
            label_font = QFont("Arial")
            label_font.setPointSizeF(max(1.0, _char_h * 0.5))
            painter.setPen(QPen(t.text_primary)); painter.setFont(label_font)
            painter.drawText(rect.adjusted(6,0,0,0), Qt.AlignVCenter|Qt.AlignLeft, "â€”")
            painter.end(); return
        consensus = self._model.get_consensus(sequences)
        if not consensus: painter.end(); return
        cw = self._get_char_width(); view_left = self._get_view_left()
        if cw <= 0: painter.end(); return
        self._sync_font_from_viewer(); painter.setFont(self._font)
        mode = self._effective_mode()
        # Annotation lane yÃ¼ksekliklerini hesapla
        _anns = list(self._alignment_model.consensus_annotations) if self._alignment_model.is_aligned else []
        _above_anns, _ = partition_annotations_by_side(_anns)
        _above_h = float(side_strip_height(_above_anns))
        seq_char_h = float(int(round(self._sequence_viewer.char_height)))
        seq_top = _above_h  # dizi bu y'den baÅŸlar
        length = len(consensus)
        start_col = max(0, int(math.floor(view_left / cw)))
        end_col = min(length, int(math.ceil((view_left + width) / cw)))
        sel_ranges = self._selection_ranges  # [(start_incl, end_excl), ...]
        ch = seq_char_h  # dizi satÄ±rÄ±nÄ±n yÃ¼ksekliÄŸi
        if mode == "line":
            line_h = ch * 0.3; y = seq_top + (ch - line_h) / 2.0
            x_start = max(0.0, start_col * cw - view_left)
            x_end = min(end_col * cw - view_left, float(width))
            draw_width = max(0.0, x_end - x_start)
            painter.setBrush(QBrush(t.seq_line_fg)); painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(x_start, y, draw_width, line_h))
            if sel_ranges:
                sel_color = QColor(t.seq_selection_bg)
                painter.setBrush(QBrush(sel_color))
                for sel_s, sel_e in sel_ranges:
                    sx = sel_s * cw - view_left; sw = (sel_e - sel_s) * cw
                    sx2 = max(0.0, sx); sw2 = min(sw - (sx2 - sx), float(width) - sx2)
                    if sw2 > 0:
                        painter.drawRect(QRectF(sx2, seq_top, sw2, ch))
            _paint_dim_overlay(painter, self._sequence_viewer, cw, float(width), float(height), t)
            painter.end(); return
        if sel_ranges:
            sel_color = QColor(t.seq_selection_bg)
            painter.setBrush(QBrush(sel_color)); painter.setPen(Qt.NoPen)
            for sel_s, sel_e in sel_ranges:
                sel_l = max(sel_s, start_col); sel_r = min(sel_e, end_col)
                if sel_r > sel_l:
                    for i in range(sel_l, sel_r):
                        painter.drawRect(QRectF(i * cw - view_left, seq_top, cw, ch))
        font_pt = self._font.pointSizeF()
        box_ref = min(ch * 0.7, font_pt); box_h = max(box_ref, 1.0); box_y = seq_top + (ch - box_h) / 2.0
        for col in range(start_col, end_col):
            base = consensus[col].upper(); x = col * cw - view_left
            is_selected = any(s <= col < e for s, e in sel_ranges)
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
            from sequence_viewer.settings.annotation_styles import annotation_style_manager as _asm_cr
            _LANE_H = _asm_cr.get_lane_height()
            above_anns, below_anns = partition_annotations_by_side(annotations)
            above_geometry = build_side_geometry(above_anns)
            below_geometry = build_side_geometry(below_anns)
            above_assignment = above_geometry.lane_assignment
            below_assignment = below_geometry.lane_assignment
            above_h = side_strip_height(above_anns)
            # dizi alanÄ± above_h'den baÅŸlar
            seq_top = float(above_h)
            painter.setRenderHint(QPainter.Antialiasing, True)
            widget_w = float(width)
            parent_by_id = {ann.id: ann for ann in annotations}
            for ann in annotations:
                x = ann.start * cw - view_left
                w_ann = cw if ann.type == AnnotationType.MISMATCH_MARKER else ann.length() * cw
                if x + w_ann < 0 or x > widget_w: continue
                clipped_x = max(x, 0.0)
                clipped_w = min(w_ann - (clipped_x - x), widget_w - clipped_x)
                if clipped_w <= 0: continue
                ann_char_w = clipped_w / max(ann.length(), 1)
                parent = parent_by_id.get(ann.parent_id)
                is_above = parent.type.is_above_sequence() if ann.type == AnnotationType.MISMATCH_MARKER and parent is not None else ann.type.is_above_sequence()
                if is_above:
                    lane = above_assignment.get(ann.id, 0)
                    ann_y = above_geometry.marker_y(above_assignment.get(ann.parent_id, 0), above=True, lane_height=_LANE_H) if ann.type == AnnotationType.MISMATCH_MARKER else above_geometry.parent_y(lane, above=True, lane_height=_LANE_H)
                else:
                    lane = below_assignment.get(ann.id, 0)
                    ann_y = seq_top + ch + (below_geometry.marker_y(below_assignment.get(ann.parent_id, 0), above=False, lane_height=_LANE_H) if ann.type == AnnotationType.MISMATCH_MARKER else below_geometry.parent_y(lane, above=False, lane_height=_LANE_H))
                ann_h_draw = _LANE_H
                ann_color = ann.resolved_color()
                ann_strand = getattr(ann, 'strand', '+')
                painter.save()
                if ann.type == AnnotationType.PRIMER:
                    draw_primer(painter, clipped_x, ann_y, clipped_w, ann_h_draw, ann_color, ann.label, strand=ann_strand, char_width=ann_char_w)
                elif ann.type == AnnotationType.PROBE:
                    draw_probe(painter, clipped_x, ann_y, clipped_w, ann_h_draw, ann_color, ann.label, strand=ann_strand, char_width=ann_char_w)
                elif ann.type == AnnotationType.MISMATCH_MARKER:
                    draw_mismatch_marker(
                        painter, clipped_x, ann_y, clipped_w, ann_h_draw,
                        ann_color,
                        ann.expected_base or ann.mismatch_base or ann.label,
                        char_width=cw,
                        font_family=self._font.family(),
                        font_size=display_settings_manager.consensus_font_size_base,
                    )
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

        # ---- SeÃ§im odak efekti ----
        _paint_dim_overlay(painter, self._sequence_viewer, cw, float(width), float(height), t)

        # ---- Dikey kÄ±lavuz Ã§izgileri ----
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

        # ---- I-beam caret (yalnÄ±zca consensus row tÄ±klamasÄ±nda, row == -1) ----
        caret = getattr(self._sequence_viewer, '_caret', None)
        if caret is not None and caret[1] == -1:
            hbar = self._sequence_viewer.horizontalScrollBar()
            offset = float(hbar.value())
            vp_w = float(self.width())
            vp_x = caret[0] * cw - offset
            if -10 <= vp_x <= vp_w + 10:
                caret_color = QColor(theme_manager.current.i_beam)
                caret_color.setAlpha(255)
                pen = QPen(caret_color, 3, Qt.SolidLine)
                pen.setCapStyle(Qt.FlatCap)
                painter.setPen(pen)
                painter.drawLine(QPointF(vp_x, seq_top), QPointF(vp_x, seq_top + seq_char_h))

        painter.end()


