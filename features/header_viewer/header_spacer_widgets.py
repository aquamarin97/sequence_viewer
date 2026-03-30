# features/header_viewer/header_spacer_widgets.py
"""
MODIFIED:
- ConsensusSpacerWidget: click = select all consensus, double-click = edit name
- ConsensusSpacerWidget: visibility synced with consensus row
"""
from __future__ import annotations
from typing import Optional
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont
from PyQt5.QtWidgets import QWidget, QLineEdit
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
    clicked = pyqtSignal()           # tek tıklama → consensus select all
    doubleClicked = pyqtSignal()     # çift tıklama → label düzenleme
    labelChanged = pyqtSignal(str)   # düzenleme tamamlandı

    def __init__(self, height=20, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self._label = "Consensus"
        self._edit_widget: Optional[QLineEdit] = None
        theme_manager.themeChanged.connect(lambda _: self.update())

    @property
    def label(self): return self._label
    @label.setter
    def label(self, value): self._label = value; self.update()

    def paintEvent(self, event):
        if not self.isVisible() or self.height() == 0: return
        painter = QPainter(self); t = theme_manager.current; rect = self.rect()
        painter.fillRect(rect, QBrush(t.row_bg_odd))
        font = QFont("Arial", 8); font.setItalic(True)
        painter.setFont(font); painter.setPen(QPen(t.text_primary))
        painter.drawText(rect.adjusted(6,0,0,0), Qt.AlignVCenter|Qt.AlignLeft, self._label)
        painter.setPen(QPen(t.border_normal))
        painter.drawLine(rect.left(), rect.bottom()-1, rect.right(), rect.bottom()-1)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
        else: super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
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
        editor.setGeometry(margin, margin, self.width() - margin*2, self.height() - margin*2)
        text_color = t.text_primary.name()
        editor.setStyleSheet(
            f"QLineEdit {{"
            f"  color: {text_color};"
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
