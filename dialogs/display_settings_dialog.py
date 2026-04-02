from __future__ import annotations
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QSpinBox,
    QDialogButtonBox, QVBoxLayout,
)
from settings.display_settings_manager import display_settings_manager


def _monospace_families() -> list[str]:
    db = QFontDatabase()
    return sorted(
        f for f in db.families()
        if db.isFixedPitch(f)
    )


class DisplaySettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Display Settings")
        self.setMinimumWidth(320)

        families = _monospace_families()

        self._seq_combo = QComboBox()
        self._seq_combo.addItems(families)

        self._seq_size_spin = QSpinBox()
        self._seq_size_spin.setRange(6, 24)
        self._seq_size_spin.setSuffix(" pt")

        self._con_combo = QComboBox()
        self._con_combo.addItems(families)

        # Mevcut değerleri set et
        self._select(self._seq_combo, display_settings_manager.sequence_font_family)
        self._seq_size_spin.setValue(display_settings_manager.sequence_font_size)
        self._select(self._con_combo, display_settings_manager.consensus_font_family)

        form = QFormLayout()
        form.addRow("Sequence font:", self._seq_combo)
        form.addRow("Sequence font size:", self._seq_size_spin)
        form.addRow("Consensus font:", self._con_combo)

        buttons = QDialogButtonBox()
        apply_btn = buttons.addButton("Uygula", QDialogButtonBox.AcceptRole)
        buttons.addButton("İptal", QDialogButtonBox.RejectRole)
        apply_btn.clicked.connect(self._apply)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------

    @staticmethod
    def _select(combo: QComboBox, family: str):
        idx = combo.findText(family)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _apply(self):
        display_settings_manager.apply({
            "font": {
                "sequence_font_family":  self._seq_combo.currentText(),
                "sequence_font_size":    self._seq_size_spin.value(),
                "consensus_font_family": self._con_combo.currentText(),
            }
        })
        self.accept()
