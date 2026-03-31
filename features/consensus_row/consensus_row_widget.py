# features/consensus_row/consensus_row_widget.py
"""
MODIFIED:
- init_state: gizli (is_aligned==False iken). is_aligned==True olunca görünür.
- alignmentStateChanged sinyaline bağlı.
"""
from __future__ import annotations
import math
from typing import Optional, Tuple
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QScrollBar
from features.consensus_row.consensus_row_model import ConsensusRowModel
from graphics.sequence_item.sequence_glyph_cache import GLYPH_CACHE
from model.alignment_data_model import AlignmentDataModel
from model.consensus_calculator import ConsensusMethod
from settings.theme import theme_manager

class ConsensusRowWidget(QWidget):
    def __init__(self, alignment_model, sequence_viewer, parent=None):
        super().__init__(parent)
        self._alignment_model = alignment_model
        self._sequence_viewer = sequence_viewer
        self._model = ConsensusRowModel(method=ConsensusMethod.PLURALITY)
        self._font = QFont("Courier New")
        self._font.setStyleHint(QFont.Monospace); self._font.setFixedPitch(True)
        from settings.color_styles import color_style_manager as _csm
        self._color_map = _csm.consensus_nucleotide_color_map()
        self._selection = None; self._press_col = None; self._is_selected = False
        self._press_pos = None; self._drag_started = False; self._press_scene_col = None
        ch = int(round(sequence_viewer.char_height))
        self.setFixedHeight(ch)
        self.setMinimumWidth(0); self.setMouseTracking(True); self.setFocusPolicy(Qt.ClickFocus)
        self.setCursor(Qt.IBeamCursor)

        self._alignment_model.rowAppended.connect(self._on_data_changed)
        self._alignment_model.rowRemoved.connect(self._on_data_changed)
        self._alignment_model.rowMoved.connect(self._on_data_changed)
        self._alignment_model.modelReset.connect(self._on_data_changed)
        # is_aligned durumuna göre görünürlüğü güncelle
        self._alignment_model.alignmentStateChanged.connect(self._on_alignment_changed)

        hbar = self._sequence_viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self.update); hbar.rangeChanged.connect(self.update)
        anim = getattr(self._sequence_viewer, "_zoom_animation", None)
        if anim: anim.valueChanged.connect(self.update)
        theme_manager.themeChanged.connect(lambda _: self._on_theme_changed())
        try:
            from settings.color_styles import color_style_manager as _csm2
            _csm2.stylesChanged.connect(self._on_color_styles_changed)
        except: pass

        # Başlangıçta gizli
        self._update_visibility()

    def _update_visibility(self):
        """is_aligned durumuna göre görünürlüğü ayarla."""
        if self._alignment_model.is_aligned:
            ch = int(round(self._sequence_viewer.char_height))
            self.setFixedHeight(ch)
            self.setVisible(True)
        else:
            self.setFixedHeight(0)
            self.setVisible(False)

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

    def clear_selection(self): self._selection = None; self._is_selected = False; self.update()

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

    def _get_char_width(self):
        if hasattr(self._sequence_viewer, "_get_current_char_width"):
            return float(self._sequence_viewer._get_current_char_width())
        return float(self._sequence_viewer.char_width)

    def _get_view_left(self): return float(self._sequence_viewer.horizontalScrollBar().value())

    def _sync_font_from_viewer(self):
        items = getattr(self._sequence_viewer, "sequence_items", None)
        if items:
            size = float(items[0]._model.current_font_size)
        else:
            cw = self._get_char_width()
            cw_default = float(getattr(self._sequence_viewer, "char_width", 12.0)) or 12.0
            scale = cw / cw_default
            if scale >= 1.8: size = 12.0
            elif scale >= 1.2: size = 10.0
            elif scale >= 0.7: size = 8.0
            else: size = max(1.0, 18.0 * 0.6 * scale)
        self._font.setPointSizeF(size)

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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
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
            event.accept()
        else: super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is None:
            super().mouseMoveEvent(event); return

        delta = (event.pos() - self._press_pos).manhattanLength()
        _DRAG_THRESHOLD_PX = 4

        if not self._drag_started and delta >= _DRAG_THRESHOLD_PX:
            self._drag_started = True
            # Ctrl yoksa guide'ları temizle
            ctrl = getattr(self._get_controller(), '_v_guide_cols', None)
            if not bool(event.modifiers() & Qt.ControlModifier):
                c = self._get_controller()
                if c is not None:
                    c._v_guide_cols.clear()
                    self._sequence_viewer.set_v_guides(c._v_guide_cols)
            self.setCursor(Qt.SizeHorCursor)

        if self._drag_started:
            col = self._scene_col_at_x(float(event.pos().x()))
            start = self._press_scene_col
            if start is not None:
                lo, hi = min(start, col), max(start, col)
                if hi > lo:
                    self._selection = (lo, hi)
                    # Guide'ları canlı güncelle
                    c = self._get_controller()
                    if c is not None:
                        left_b, right_b = lo, hi + 1
                        live = [g for g in c._v_guide_cols if g not in (left_b, right_b)]
                        live += [left_b, right_b]
                        self._sequence_viewer.set_v_guides(live)
                else:
                    self._selection = None
                    c = self._get_controller()
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
                        ctrl = bool(event.modifiers() & Qt.ControlModifier)
                        if not ctrl:
                            c._v_guide_cols.clear()
                        for b in (lo, hi + 1):
                            if b not in c._v_guide_cols:
                                c._v_guide_cols.append(b)
                        self._sequence_viewer.set_v_guides(c._v_guide_cols)
            else:
                # Drag yok → boundary tıklama → guide
                self._press_pos = None
                self._drag_started = False
                self._selection = None
                boundary_col = self._boundary_col_at_x(float(event.pos().x()))
                c = self._get_controller()
                if c is not None:
                    ctrl = bool(event.modifiers() & Qt.ControlModifier)
                    if ctrl:
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
        if ctrl and shift and event.key() == Qt.Key_C:
            self._copy_fasta(); event.accept()
        elif ctrl and not shift and event.key() == Qt.Key_C:
            self._copy_sequence(); event.accept()
        else: super().keyPressEvent(event)

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
        # Seçim vurgusu: her zaman row_bg_odd arka plan, seçimde hafif overlay
        is_selected = self._is_selected
        painter.fillRect(rect, QBrush(t.row_bg_odd))
        if is_selected:
            band = QColor(t.row_band_highlight)
            painter.fillRect(rect, QBrush(band))
        # Sol kenar çizgisi (seçili iken)
        if is_selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(t.drop_indicator))
            painter.drawRect(0, 0, 2, height)
        painter.setPen(QPen(t.border_normal)); painter.drawLine(0, height-1, width, height-1)
        sequences = [seq for _, seq in self._alignment_model.all_rows()]
        if not sequences:
            label_font = QFont("Arial")
            label_font.setPointSizeF(max(1.0, height * 0.5))
            painter.setPen(QPen(t.text_primary)); painter.setFont(label_font)
            painter.drawText(rect.adjusted(6,0,0,0), Qt.AlignVCenter|Qt.AlignLeft, "—")
            painter.end(); return
        consensus = self._model.get_consensus(sequences)
        if not consensus: painter.end(); return
        cw = self._get_char_width(); view_left = self._get_view_left()
        if cw <= 0: painter.end(); return
        self._sync_font_from_viewer(); painter.setFont(self._font)
        mode = self._effective_mode(); ch = float(height); length = len(consensus)
        start_col = max(0, int(math.floor(view_left / cw)))
        end_col = min(length, int(math.ceil((view_left + width) / cw)))
        sel_start = sel_end = None
        if self._selection: sel_start, sel_end = self._selection
        sel_alpha = 110 if t.name == "dark" else 120
        if mode == "line":
            line_h = ch * 0.3; y = (ch - line_h) / 2.0
            x_start = max(0.0, start_col * cw - view_left)
            x_end = min(end_col * cw - view_left, float(width))
            draw_width = max(0.0, x_end - x_start)
            painter.setBrush(QBrush(t.seq_line_fg)); painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(x_start, y, draw_width, line_h))
            if sel_start is not None and sel_end is not None:
                sx = sel_start * cw - view_left; sw = (sel_end - sel_start + 1) * cw
                sx2 = max(0.0, sx); sw2 = min(sw - (sx2 - sx), float(width) - sx2)
                if sw2 > 0:
                    sel_color = QColor(t.seq_selection_bg); sel_color.setAlpha(sel_alpha)
                    painter.setBrush(QBrush(sel_color)); painter.drawRect(QRectF(sx2, 0, sw2, ch))
            painter.end(); return
        if sel_start is not None and sel_end is not None:
            sel_l = max(sel_start, start_col); sel_r = min(sel_end + 1, end_col)
            if sel_r > sel_l:
                sel_color = QColor(t.seq_selection_bg); sel_color.setAlpha(sel_alpha)
                painter.setBrush(QBrush(sel_color)); painter.setPen(Qt.NoPen)
                for i in range(sel_l, sel_r):
                    painter.drawRect(QRectF(i * cw - view_left, 0, cw, ch))
        font_pt = self._font.pointSizeF()
        box_ref = min(ch * 0.7, font_pt); box_h = max(box_ref, 1.0); box_y = (ch - box_h) / 2.0
        for col in range(start_col, end_col):
            base = consensus[col].upper(); x = col * cw - view_left
            color = self._color_map.get(base, t.text_primary)
            if mode == "box":
                painter.setBrush(QBrush(color)); painter.setPen(Qt.NoPen)
                painter.drawRect(QRectF(x, box_y, cw, box_h))
            else:
                glyph = GLYPH_CACHE.get_glyph(base, self._font, color)
                dx = x + (cw - glyph.width()) / 2.0; dy = (ch - glyph.height()) / 2.0
                painter.drawPixmap(int(dx), int(dy), glyph)
        painter.end()