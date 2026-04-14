from __future__ import annotations

from PyQt5.QtWidgets import QLineEdit

from sequence_viewer.settings.theme import theme_manager


class ConsensusSpacerEditor:
    def __init__(self, widget) -> None:
        self._widget = widget
        self._editor: QLineEdit | None = None

    def start_edit(self, text: str) -> None:
        if self._editor is not None:
            return
        theme = theme_manager.current
        editor = QLineEdit(self._widget)
        editor.setText(text)
        editor.selectAll()
        margin = 2
        editor_h = max(self._widget.height() - margin * 2, 22)
        y_pos = max(0, (self._widget.height() - editor_h) // 2)
        editor.setGeometry(margin, y_pos, self._widget.width() - margin * 2, editor_h)
        editor.setStyleSheet(
            f"QLineEdit {{"
            f"  color: {theme.text_primary.name()};"
            f"  background: {theme.editor_bg};"
            f"  border: 1.5px solid {theme.editor_border};"
            f"  border-radius: 2px;"
            f"  padding: 0px 4px;"
            f"  font-family: Arial;"
            f"  font-size: 8pt;"
            f"  font-style: italic;"
            f"}}"
        )
        editor.show()
        editor.setFocus()
        editor.returnPressed.connect(self.commit_edit)
        editor.editingFinished.connect(self.commit_edit)
        self._editor = editor

    def commit_edit(self) -> str | None:
        if self._editor is None:
            return None
        new_text = self._editor.text().strip()
        editor = self._editor
        self._editor = None
        editor.blockSignals(True)
        editor.hide()
        editor.deleteLater()
        return new_text or None
