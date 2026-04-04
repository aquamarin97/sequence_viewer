from __future__ import annotations
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDoubleSpinBox,
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

        self._con_combo = QComboBox()
        self._con_combo.addItems(families)

        self._seq_base_spin = QDoubleSpinBox()
        self._seq_base_spin.setRange(8.0, 32.0)
        self._seq_base_spin.setSingleStep(1.0)
        self._seq_base_spin.setDecimals(0)
        self._seq_base_spin.setSuffix(" pt")

        # Mevcut değerleri set et
        self._select(self._seq_combo, display_settings_manager.sequence_font_family)
        self._select(self._con_combo, display_settings_manager.consensus_font_family)
        self._seq_base_spin.setValue(display_settings_manager.sequence_font_size_base)

        form = QFormLayout()
        form.addRow("Sequence font:", self._seq_combo)
        form.addRow("Consensus font:", self._con_combo)
        form.addRow("Sequence Font Size:", self._seq_base_spin)

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
                "sequence_font_family":    self._seq_combo.currentText(),
                "consensus_font_family":   self._con_combo.currentText(),
                "sequence_font_size_base": self._seq_base_spin.value(),
            }
        })
        self.accept()
