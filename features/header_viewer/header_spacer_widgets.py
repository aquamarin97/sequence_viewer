# features/header_viewer/header_spacer_widgets.py
"""
MODIFIED:
- ConsensusSpacerWidget: click = select all consensus, double-click = edit name
- ConsensusSpacerWidget: visibility synced with consensus row
"""
from __future__ import annotations
from typing import Optional
from PyQt5.QtCore import Qt, pyqtSignal, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont, QColor
from PyQt5.QtWidgets import QWidget, QLineEdit
from settings.mouse_binding_manager import mouse_binding_manager, MouseAction
from settings.theme import theme_manager

class HeaderTopWidget(QWidget):
    def __init__(self, height=28, parent=None):
        super().__init__(parent); self.setFixedHeight(height)
        theme_manager.themeChanged.connect(lambda _: self.update())
    def paintEvent(self, event):
        painter = QPainter(self); t = theme_manager.current
        painter.fillRect(self.rect(), QBrush(t.ruler_bg))
        painter.setPen(QPen(t.ruler_border))
        painter.drawLine(0, self.rect().bottom()-1, self.rect().right(), self.rect().bottom()-1)
        painter.end()

class HeaderPositionSpacerWidget(QWidget):
    def __init__(self, height=24, parent=None):
        super().__init__(parent); self.setFixedHeight(height)
        theme_manager.themeChanged.connect(lambda _: self.update())
    def paintEvent(self, event):
        painter = QPainter(self); t = theme_manager.current; rect = self.rect()
        painter.fillRect(rect, QBrush(t.ruler_bg))
        font = QFont("Arial", 9); painter.setFont(font); painter.setPen(QPen(t.ruler_fg))
        painter.drawText(rect.adjusted(6,0,0,0), Qt.AlignVCenter|Qt.AlignLeft, "Header")
        painter.setPen(QPen(t.ruler_border))
        painter.drawLine(rect.left(), rect.bottom()-1, rect.right(), rect.bottom()-1)
        painter.end()

class AnnotationSpacerWidget(QWidget):
    def __init__(self, height=24, parent=None):
        super().__init__(parent); self.setFixedHeight(height)
        theme_manager.themeChanged.connect(lambda _: self.update())
    def sync_height(self, height):
        if self.height() != height: self.setFixedHeight(height)
    def paintEvent(self, event):
        painter = QPainter(self); t = theme_manager.current; rect = self.rect()
        painter.fillRect(rect, QBrush(t.row_bg_even))
        font = QFont("Arial", 8); font.setItalic(True)
        painter.setFont(font); painter.setPen(QPen(t.text_primary))
        painter.drawText(rect.adjusted(6,0,0,0), Qt.AlignVCenter|Qt.AlignLeft, "Annotations")
        painter.setPen(QPen(t.border_normal))
        painter.drawLine(rect.left(), rect.bottom()-1, rect.right(), rect.bottom()-1)
        painter.end()

class ConsensusSpacerWidget(QWidget):
    """
    Consensus satırı ile hizalı sol panel spacer'ı.
    
    Tek tıklama: consensus dizisini tümüyle seçer.
    Çift tıklama: consensus etiketini düzenlemeye açar.
    """
    clicked = pyqtSignal(bool)       # tek tıklama → consensus select all (bool=ctrl)
    doubleClicked = pyqtSignal()     # çift tıklama → label düzenleme
    labelChanged = pyqtSignal(str)   # düzenleme tamamlandı

    def __init__(self, height=20, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self._char_height = height
        self._above_h = 0  # annotation lane yüksekliği (üstte)
        self._label = "Consensus"
        self._selected = False
        self._edit_widget: Optional[QLineEdit] = None
        self.setFocusPolicy(Qt.ClickFocus)
        theme_manager.themeChanged.connect(lambda _: self.update())

    def sync_seq_region(self, above_h: float, char_h: float):
        """Sequence satırının konumunu güncelle (annotation eklenince çağrılır)."""
        self._above_h = above_h
        self._char_height = char_h
        self.update()

    def _label_font(self):
        font = QFont("Arial")
        font.setItalic(True)
        font.setPointSizeF(max(1.0, self._char_height * 0.5))
        return font

    @property
    def label(self): return self._label
    @label.setter
    def label(self, value): self._label = value; self.update()

    def set_selected(self, selected: bool):
        if self._selected == selected: return
        self._selected = selected; self.update()

    def paintEvent(self, event):
        if not self.isVisible() or self.height() == 0: return
        painter = QPainter(self); t = theme_manager.current; rect = self.rect()
        bg = QColor(t.row_band_highlight) if self._selected else t.row_bg_odd
        painter.fillRect(rect, QBrush(bg))
        if self._selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(t.drop_indicator))
            painter.drawRect(0, 0, 2, rect.height())
        font = self._label_font()
        painter.setFont(font)
        text_color = t.text_selected if self._selected else t.text_primary
        painter.setPen(QPen(text_color))
        text_left = 9 if self._selected else 6
        # Metni _char_height alanının altına hizala (sequence ile aynı hiza)
        text_rect = QRectF(text_left, self._above_h, rect.width() - text_left, self._char_height)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._label)
        painter.setPen(QPen(t.border_normal))
        painter.drawLine(rect.left(), rect.bottom()-1, rect.right(), rect.bottom()-1)
        painter.end()

    def mousePressEvent(self, event):
        action = mouse_binding_manager.resolve_consensus_spacer_click(event.modifiers(), event.button())
        if action in (MouseAction.CONSENSUS_SELECT_ALL, MouseAction.CONSENSUS_SELECT_ADDITIVE):
            self.setFocus()
            ctrl = action == MouseAction.CONSENSUS_SELECT_ADDITIVE
            self.clicked.emit(ctrl)
            event.accept()
        else: super().mousePressEvent(event)

    def keyPressEvent(self, event):
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        if ctrl and shift and event.key() == Qt.Key_C:
            self._copy_fasta(); event.accept()
        elif ctrl and not shift and event.key() == Qt.Key_C:
            self._copy_sequence(); event.accept()
        else: super().keyPressEvent(event)

    def _get_consensus_row(self):
        """Parent zincirinden ConsensusRowWidget'ı bul."""
        p = self.parent()
        while p is not None:
            if hasattr(p, 'consensus_row'):
                return p.consensus_row
            p = p.parent()
        return None

    def _copy_sequence(self):
        from PyQt5.QtWidgets import QApplication
        row = self._get_consensus_row()
        if row is None: return
        row._copy_sequence()

    def _copy_fasta(self):
        from PyQt5.QtWidgets import QApplication
        row = self._get_consensus_row()
        if row is None: return
        row._copy_fasta()

    def mouseDoubleClickEvent(self, event):
        if mouse_binding_manager.is_consensus_spacer_edit_event(event.modifiers(), event.button()):
            self._start_edit()
            event.accept()
        else: super().mouseDoubleClickEvent(event)

    def _start_edit(self):
        if self._edit_widget is not None: return
        t = theme_manager.current
        editor = QLineEdit(self)
        editor.setText(self._label)
        editor.selectAll()
        margin = 2
        editor_h = max(self.height() - margin * 2, 22)
        # Editor widget yüksekten taşıyorsa yukarı kaydır
        y_pos = max(0, (self.height() - editor_h) // 2)
        editor.setGeometry(margin, y_pos, self.width() - margin * 2, editor_h)
        editor.setStyleSheet(
            f"QLineEdit {{"
            f"  color: {t.text_primary.name()};"
            f"  background: {t.editor_bg};"
            f"  border: 1.5px solid {t.editor_border};"
            f"  border-radius: 2px;"
            f"  padding: 0px 4px;"
            f"  font-family: Arial;"
            f"  font-size: 8pt;"
            f"  font-style: italic;"
            f"}}")
        editor.show(); editor.setFocus()
        editor.returnPressed.connect(self._commit_edit)
        editor.editingFinished.connect(self._commit_edit)
        self._edit_widget = editor

    def _commit_edit(self):
        if self._edit_widget is None: return
        new_text = self._edit_widget.text().strip()
        editor = self._edit_widget
        self._edit_widget = None
        editor.blockSignals(True); editor.hide(); editor.deleteLater()
        if new_text and new_text != self._label:
            self._label = new_text
            self.labelChanged.emit(self._label)
            self.update()
