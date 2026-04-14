from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QWidget

from sequence_viewer.features.consensus_row.consensus_spacer_editor import (
    ConsensusSpacerEditor,
)
from sequence_viewer.settings.mouse_binding_manager import MouseAction, mouse_binding_manager
from sequence_viewer.settings.theme import theme_manager


class ConsensusSpacerWidget(QWidget):
    clicked = pyqtSignal(bool)
    doubleClicked = pyqtSignal()
    labelChanged = pyqtSignal(str)
    copySequenceRequested = pyqtSignal()
    copyFastaRequested = pyqtSignal()

    def __init__(self, height=20, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self._char_height = height
        self._above_h = 0
        self._label = "Consensus"
        self._selected = False
        self._editor = ConsensusSpacerEditor(self)
        self.setFocusPolicy(Qt.ClickFocus)
        theme_manager.themeChanged.connect(lambda _: self.update())

    def sync_seq_region(self, above_h: float, char_h: float):
        self._above_h = above_h
        self._char_height = char_h
        self.update()

    def _label_font(self):
        font = QFont("Arial")
        font.setItalic(True)
        font.setPointSizeF(max(1.0, self._char_height * 0.5))
        return font

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        self._label = value
        self.update()

    @property
    def is_selected(self) -> bool:
        return self._selected

    def set_selected(self, selected: bool):
        if self._selected == selected:
            return
        self._selected = selected
        self.update()

    def paintEvent(self, event):
        if not self.isVisible() or self.height() == 0:
            return
        painter = QPainter(self)
        theme = theme_manager.current
        rect = self.rect()
        bg = QColor(theme.row_band_highlight) if self._selected else theme.row_bg_odd
        painter.fillRect(rect, QBrush(bg))
        if self._selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(theme.drop_indicator))
            painter.drawRect(0, 0, 2, rect.height())
        painter.setFont(self._label_font())
        text_color = theme.text_selected if self._selected else theme.text_primary
        painter.setPen(QPen(text_color))
        text_left = 9 if self._selected else 6
        text_rect = QRectF(text_left, self._above_h, rect.width() - text_left, self._char_height)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._label)
        painter.setPen(QPen(theme.border_normal))
        painter.drawLine(rect.left(), rect.bottom() - 1, rect.right(), rect.bottom() - 1)
        painter.end()

    def mousePressEvent(self, event):
        action = mouse_binding_manager.resolve_consensus_spacer_click(event.modifiers(), event.button())
        if action in (MouseAction.CONSENSUS_SELECT_ALL, MouseAction.CONSENSUS_SELECT_ADDITIVE):
            self.setFocus()
            self.clicked.emit(action == MouseAction.CONSENSUS_SELECT_ADDITIVE)
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        if ctrl and shift and event.key() == Qt.Key_C:
            self.copyFastaRequested.emit()
            event.accept()
            return
        if ctrl and not shift and event.key() == Qt.Key_C:
            self.copySequenceRequested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if mouse_binding_manager.is_consensus_spacer_edit_event(event.modifiers(), event.button()):
            self.doubleClicked.emit()
            self._editor.start_edit(self._label)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def commit_edit_if_needed(self) -> None:
        new_text = self._editor.commit_edit()
        if new_text and new_text != self._label:
            self._label = new_text
            self.labelChanged.emit(self._label)
            self.update()
