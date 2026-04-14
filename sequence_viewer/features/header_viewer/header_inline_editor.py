from __future__ import annotations

from PyQt5.QtWidgets import QLineEdit

from sequence_viewer.settings.theme import theme_manager


class HeaderInlineEditor:
    def __init__(self, view) -> None:
        self._view = view
        self._widget = None
        self._editing_row = None

    @property
    def editing_row(self):
        return self._editing_row

    def is_editing(self, row=None) -> bool:
        if row is None:
            return self._widget is not None
        return self._widget is not None and self._editing_row == row

    def start_edit(self, row_index: int, item, viewport_top: float, viewport_width: int, char_height: int) -> None:
        if row_index < 0:
            return
        self.cancel_edit()
        editor = QLineEdit(self._view.viewport())
        full_text = item.full_text
        raw_header = full_text.split(". ", 1)[1] if ". " in full_text else full_text
        editor.setText(raw_header)
        editor.selectAll()
        margin = 2
        min_editor_h = max(char_height - margin * 2, 22)
        editor.setGeometry(margin, int(viewport_top) + margin, viewport_width - margin * 2, min_editor_h)
        self._apply_style(editor, item)
        editor.show()
        editor.setFocus()
        editor.returnPressed.connect(self.commit_edit)
        editor.editingFinished.connect(self.commit_edit)
        self._widget = editor
        self._editing_row = row_index
        item.set_hovered(True)

    def refresh_style(self, header_items) -> None:
        if self._widget is None or self._editing_row is None:
            return
        row = self._editing_row
        if 0 <= row < len(header_items):
            self._apply_style(self._widget, header_items[row])

    def commit_edit(self) -> None:
        if self._widget is None or self._editing_row is None:
            return
        new_text = self._widget.text().strip()
        row_index = self._editing_row
        self.cancel_edit()
        if new_text:
            self._view._on_edit_committed(row_index, new_text)

    def cancel_edit(self) -> None:
        widget = self._widget
        self._widget = None
        if widget is not None:
            widget.blockSignals(True)
            widget.hide()
            widget.deleteLater()
        if self._editing_row is not None:
            row = self._editing_row
            self._editing_row = None
            if 0 <= row < len(self._view.header_items):
                self._view.header_items[row].set_hovered(False)

    def _apply_style(self, editor, item) -> None:
        theme = theme_manager.current
        editor.setStyleSheet(
            f"QLineEdit {{color:{theme.text_primary.name()};background:{theme.editor_bg};"
            f"border:1.5px solid {theme.editor_border};border-radius:2px;padding:0px 4px;"
            f"font-family:Arial;font-size:{int(item._model.compute_font_point_size())}pt;}}"
        )
