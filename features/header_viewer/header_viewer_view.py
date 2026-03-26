# features/header_viewer/header_viewer_view.py

from __future__ import annotations

import math
from typing import FrozenSet, List, Optional

from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import QPainter, QFontMetrics, QPen, QBrush, QColor
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QLineEdit

from graphics.header_item.header_item import HeaderRowItem
from model.row_selection_model import RowSelectionModel
from settings.theme import theme_manager


_DRAG_THRESHOLD_PX = 6
_DROP_LINE_WIDTH   = 2


class HeaderViewerView(QGraphicsView):
    """
    Header satırlarını çizen view.

    Özellikler
    ----------
    * Zebra striping (tema token'ları ile)
    * Windows tarzı satır seçimi:
        - Click          → tek satır seç
        - Ctrl+Click     → toggle
        - Shift+Click    → aralık seç
        - Ctrl+A         → tümünü seç
        - Escape         → seçimi temizle
        - Delete/Backspace → seçili satırları sil
    * Double-click → inline QLineEdit düzenleme
    * Drag & drop  → satır sıralama + drop indicator
    * Dark Mode    → theme_manager.themeChanged ile otomatik

    Hook'lar (alt sınıf override eder)
    -----------------------------------
    _on_edit_committed(row_index, new_text)
    _on_row_move_requested(from_index, to_index)
    _on_selection_changed(selected_rows)
    _on_rows_delete_requested(rows)
    """

    def __init__(
        self,
        parent=None,
        *,
        row_height: float = 18.0,
        initial_width: float = 160.0,
    ) -> None:
        super().__init__(parent)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.row_height:   int   = int(round(row_height))
        self.header_width: float = float(initial_width)

        self.header_items: List[HeaderRowItem] = []

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setMinimumWidth(60)
        self.setMaximumWidth(400)
        self.setMouseTracking(True)

        # Klavye kısayolları için focus gerekli
        self.setFocusPolicy(Qt.StrongFocus)

        # Seçim modeli
        self._selection = RowSelectionModel()

        # Inline edit
        self._edit_widget: Optional[QLineEdit] = None
        self._editing_row: Optional[int]       = None

        # Drag & drop
        self._press_pos:       Optional[QPoint] = None
        self._drag_source_row: Optional[int]    = None
        self._drag_insert_pos: Optional[int]    = None
        self._dragging:        bool             = False

        # Tema değişince tüm item'ları yeniden çiz
        theme_manager.themeChanged.connect(self._on_theme_changed)

    # ==================================================================
    # Public API: item yönetimi
    # ==================================================================

    def add_header_item(self, display_text: str) -> HeaderRowItem:
        row_index  = len(self.header_items)
        item_width = self.viewport().width() or self.header_width

        item = HeaderRowItem(
            text=display_text,
            width=item_width,
            row_height=self.row_height,
            row_index=row_index,
        )
        item.setPos(0, row_index * self.row_height)
        self.scene.addItem(item)
        self.header_items.append(item)
        self._update_scene_rect()
        return item

    def clear_items(self) -> None:
        self._cancel_edit()
        self._reset_drag_state()
        self.header_items.clear()
        self.scene.clear()
        self._update_scene_rect()

    def apply_selection_to_items(self, changed_rows: FrozenSet[int]) -> None:
        """
        Seçim modeli değiştikten sonra sadece değişen item'ları günceller.
        Tüm viewport yerine minimal repaint.
        """
        for row in changed_rows:
            if 0 <= row < len(self.header_items):
                self.header_items[row].set_selected(
                    self._selection.is_selected(row)
                )

    # ==================================================================
    # Geometri
    # ==================================================================

    def _update_scene_rect(self) -> None:
        height = len(self.header_items) * self.row_height
        width  = self.viewport().width() or self.header_width
        self.scene.setSceneRect(0, 0, width, height)

    def compute_required_width(self) -> int:
        if not self.header_items:
            return 100
        metrics   = QFontMetrics(self.header_items[0].font)
        left_pad  = 6
        right_pad = 4
        safety    = 4
        max_px    = max(
            metrics.horizontalAdvance(item.full_text)
            for item in self.header_items
        )
        return max_px + left_pad + right_pad + safety

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w = self.viewport().width()
        for item in self.header_items:
            item.set_width(w)
        self._update_scene_rect()
        required = self.compute_required_width() if self.header_items else 10
        self.setMaximumWidth(required if w >= required else 16_777_215)

    # ==================================================================
    # Koordinat yardımcıları
    # ==================================================================

    def _row_at_viewport_y(self, y: int) -> int:
        scene_y = self.mapToScene(0, y).y()
        return int(math.floor(scene_y / self.row_height))

    def _insert_pos_at_viewport_y(self, y: int) -> int:
        scene_y = self.mapToScene(0, y).y()
        insert  = int(round(scene_y / self.row_height))
        return max(0, min(insert, len(self.header_items)))

    def _item_viewport_rect(self, row_index: int) -> QRectF:
        scene_rect = QRectF(
            0, row_index * self.row_height,
            self.viewport().width(), self.row_height,
        )
        tl = self.mapFromScene(scene_rect.topLeft())
        br = self.mapFromScene(scene_rect.bottomRight())
        return QRectF(tl, br)

    # ==================================================================
    # Tema
    # ==================================================================

    def _on_theme_changed(self, _theme) -> None:
        self.viewport().update()

    # ==================================================================
    # Seçim
    # ==================================================================

    def _handle_selection(self, row: int, modifiers) -> None:
        """Mouse click modifiyelerine göre seçim modelini günceller."""
        n = len(self.header_items)
        if n == 0:
            return

        ctrl  = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)

        if ctrl and shift:
            # Ctrl+Shift: aralık seç ama mevcut seçimi koru
            # (Windows'ta Ctrl+Shift genellikle Shift ile aynı davranır)
            changed = self._selection.handle_shift_click(row, n)
        elif ctrl:
            changed = self._selection.handle_ctrl_click(row, n)
        elif shift:
            changed = self._selection.handle_shift_click(row, n)
        else:
            changed = self._selection.handle_click(row, n)

        self.apply_selection_to_items(changed)
        self._on_selection_changed(self._selection.selected_rows())

    # ==================================================================
    # Inline edit
    # ==================================================================

    def _start_edit(self, row_index: int) -> None:
        if row_index < 0 or row_index >= len(self.header_items):
            return
        self._cancel_edit()

        item     = self.header_items[row_index]
        vp_rect  = self._item_viewport_rect(row_index)

        full_text  = item.full_text
        raw_header = full_text.split(". ", 1)[1] if ". " in full_text else full_text

        t      = theme_manager.current
        editor = QLineEdit(self.viewport())
        editor.setText(raw_header)
        editor.selectAll()

        margin = 2
        editor.setGeometry(
            int(vp_rect.left()) + margin,
            int(vp_rect.top())  + margin,
            int(vp_rect.width())  - margin * 2,
            int(vp_rect.height()) - margin * 2,
        )
        editor.setStyleSheet(
            f"QLineEdit {{"
            f"  background: {t.editor_bg};"
            f"  border: 1.5px solid {t.editor_border};"
            f"  border-radius: 2px;"
            f"  padding: 0px 4px;"
            f"  font-family: Arial;"
            f"  font-size: {int(item._model.compute_font_point_size())}pt;"
            f"}}"
        )
        editor.show()
        editor.setFocus()

        editor.returnPressed.connect(lambda: self._commit_edit(row_index))
        editor.editingFinished.connect(lambda: self._commit_edit(row_index))

        self._edit_widget = editor
        self._editing_row = row_index
        item.set_hovered(True)

    def _commit_edit(self, row_index: int) -> None:
        if self._edit_widget is None or self._editing_row != row_index:
            return
        new_text = self._edit_widget.text().strip()
        self._cancel_edit()
        if not new_text:
            return
        self._on_edit_committed(row_index, new_text)

    def _cancel_edit(self) -> None:
        # ÖNCE referansı al ve None yap — hide() editingFinished tetiklerse
        # ikinci _commit_edit çağrısında guard düzgün çalışsın.
        widget = self._edit_widget
        self._edit_widget = None          # ← None ataması hide()'dan ÖNCE

        if widget is not None:
            widget.blockSignals(True)     # ← editingFinished'ı kapat
            widget.hide()
            widget.deleteLater()

        if self._editing_row is not None:
            idx = self._editing_row
            self._editing_row = None
            if 0 <= idx < len(self.header_items):
                self.header_items[idx].set_hovered(False)

    # ==================================================================
    # Drag & drop
    # ==================================================================

    def _reset_drag_state(self) -> None:
        if self._drag_source_row is not None:
            idx = self._drag_source_row
            if 0 <= idx < len(self.header_items):
                self.header_items[idx].set_dragging(False)
        self._drag_source_row = None
        self._drag_insert_pos = None
        self._dragging        = False
        self._press_pos       = None
        self.viewport().update()

    def _update_drag(self, vp_pos: QPoint) -> None:
        self._drag_insert_pos = self._insert_pos_at_viewport_y(vp_pos.y())
        self.viewport().update()

    # ==================================================================
    # Hook'lar (alt sınıf override eder)
    # ==================================================================

    def _on_edit_committed(self, row_index: int, new_text: str) -> None:
        pass

    def _on_row_move_requested(self, from_index: int, to_index: int) -> None:
        pass

    def _on_selection_changed(self, selected_rows: FrozenSet[int]) -> None:
        pass

    def _on_rows_delete_requested(self, rows: FrozenSet[int]) -> None:
        pass

    # ==================================================================
    # Mouse olayları
    # ==================================================================

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            row = self._row_at_viewport_y(event.pos().y())

            # Aktif edit varsa ve başka satıra tıklandıysa kapat
            if self._editing_row is not None and self._editing_row != row:
                self._commit_edit(self._editing_row)

            if 0 <= row < len(self.header_items):
                self._press_pos       = event.pos()
                self._drag_source_row = row
                # Seçimi hemen uygula (drag olursa override edilmez)
                self._handle_selection(row, event.modifiers())
            else:
                # Boşa tıklandı → seçimi temizle
                changed = self._selection.clear()
                self.apply_selection_to_items(changed)
                self._on_selection_changed(self._selection.selected_rows())

            self.setFocus()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (
            event.buttons() & Qt.LeftButton
            and self._press_pos is not None
            and self._drag_source_row is not None
        ):
            delta = (event.pos() - self._press_pos).manhattanLength()

            if not self._dragging and delta >= _DRAG_THRESHOLD_PX:
                self._dragging = True
                self.header_items[self._drag_source_row].set_dragging(True)
                self.viewport().setCursor(Qt.SizeVerCursor)

            if self._dragging:
                self._update_drag(event.pos())

            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            if self._dragging and self._drag_source_row is not None:
                src    = self._drag_source_row
                insert = self._drag_insert_pos if self._drag_insert_pos is not None else src
                to_idx = insert if insert <= src else insert - 1

                self._reset_drag_state()
                self.viewport().unsetCursor()

                if to_idx != src:
                    self._on_row_move_requested(src, to_idx)
            else:
                self._press_pos       = None
                self._drag_source_row = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            row = self._row_at_viewport_y(event.pos().y())
            if 0 <= row < len(self.header_items):
                self._press_pos       = None
                self._drag_source_row = None
                self._start_edit(row)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    # ==================================================================
    # Klavye kısayolları
    # ==================================================================

    def keyPressEvent(self, event) -> None:
        key  = event.key()
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        n    = len(self.header_items)

        if ctrl and key == Qt.Key_A:
            # Ctrl+A → tümünü seç
            changed = self._selection.select_all(n)
            self.apply_selection_to_items(changed)
            self._on_selection_changed(self._selection.selected_rows())
            event.accept()

        elif key == Qt.Key_Escape:
            # Escape → seçimi temizle / edit'i iptal et
            if self._edit_widget is not None:
                self._cancel_edit()
            else:
                changed = self._selection.clear()
                self.apply_selection_to_items(changed)
                self._on_selection_changed(self._selection.selected_rows())
            event.accept()

        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            # Delete → seçili satırları sil
            rows = self._selection.selected_rows()
            if rows:
                self._on_rows_delete_requested(rows)
            event.accept()

        else:
            super().keyPressEvent(event)

    # ==================================================================
    # Drop indicator çizimi
    # ==================================================================

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawForeground(painter, rect)

        if not self._dragging or self._drag_insert_pos is None:
            return

        insert_y_scene = self._drag_insert_pos * self.row_height
        vp_y           = self.mapFromScene(0, insert_y_scene).y()
        vp_width       = self.viewport().width()

        t = theme_manager.current

        painter.save()
        painter.resetTransform()

        pen = QPen(t.drop_indicator, _DROP_LINE_WIDTH)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(8, vp_y, vp_width - 4, vp_y)

        r = 4
        painter.setBrush(QBrush(t.drop_indicator))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, vp_y - r, r * 2, r * 2)

        painter.restore()