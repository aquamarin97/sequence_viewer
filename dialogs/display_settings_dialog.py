# dialogs/display_settings_dialog.py
from __future__ import annotations
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QSpinBox,
    QDialogButtonBox, QVBoxLayout, QGroupBox,
)
from model.annotation import AnnotationType
from settings.annotation_styles import annotation_style_manager
from settings.display_settings_manager import display_settings_manager


def _monospace_families() -> list[str]:
    db = QFontDatabase()
    return sorted(
        f for f in db.families()
        if db.isFixedPitch(f)
    )


def _all_families() -> list[str]:
    db = QFontDatabase()
    return sorted(db.families())


# ── Annotation tipleri ve etiketleri ──────────────────────────────────────────
_ANN_TYPES = [
    (AnnotationType.PRIMER,          "Primer"),
    (AnnotationType.PROBE,           "Probe"),
    (AnnotationType.REPEATED_REGION, "Repeated Region"),
]


class DisplaySettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Display Settings")
        self.setMinimumWidth(360)

        mono_families = _monospace_families()
        all_families  = _all_families()

        # ── Sequence / Consensus font ──────────────────────────────────────────
        self._seq_combo = QComboBox()
        self._seq_combo.addItems(mono_families)

        self._con_combo = QComboBox()
        self._con_combo.addItems(mono_families)

        self._seq_base_spin = QDoubleSpinBox()
        self._seq_base_spin.setRange(8.0, 32.0)
        self._seq_base_spin.setSingleStep(1.0)
        self._seq_base_spin.setDecimals(0)
        self._seq_base_spin.setSuffix(" pt")

        self._select(self._seq_combo, display_settings_manager.sequence_font_family)
        self._select(self._con_combo, display_settings_manager.consensus_font_family)
        self._seq_base_spin.setValue(display_settings_manager.sequence_font_size_base)

        seq_form = QFormLayout()
        seq_form.addRow("Sequence font:",   self._seq_combo)
        seq_form.addRow("Consensus font:",  self._con_combo)
        seq_form.addRow("Sequence Font Size:", self._seq_base_spin)

        seq_group = QGroupBox("Sequence / Consensus")
        seq_group.setLayout(seq_form)

        # ── Annotation label font ──────────────────────────────────────────────
        self._ann_widgets: dict[AnnotationType, dict] = {}

        ann_layout = QVBoxLayout()
        for ann_type, ann_label in _ANN_TYPES:
            style = annotation_style_manager.get(ann_type)

            family_combo = QComboBox()
            family_combo.addItems(all_families)
            self._select(family_combo, style.label_font_family)

            size_spin = QSpinBox()
            size_spin.setRange(8, 32)
            size_spin.setSingleStep(1)
            size_spin.setSuffix(" pt")
            size_spin.setValue(style.label_font_size)

            self._ann_widgets[ann_type] = {
                "family": family_combo,
                "size":   size_spin,
            }

            ann_form = QFormLayout()
            ann_form.addRow("Font Family:", family_combo)
            ann_form.addRow("Font Size:",   size_spin)

            group = QGroupBox(ann_label)
            group.setLayout(ann_form)
            ann_layout.addWidget(group)

        ann_group = QGroupBox("Annotation Labels")
        ann_group.setLayout(ann_layout)

        # ── Butonlar ──────────────────────────────────────────────────────────
        buttons = QDialogButtonBox()
        apply_btn = buttons.addButton("Uygula", QDialogButtonBox.AcceptRole)
        buttons.addButton("İptal", QDialogButtonBox.RejectRole)
        apply_btn.clicked.connect(self._apply)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(seq_group)
        layout.addWidget(ann_group)
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
        for ann_type, widgets in self._ann_widgets.items():
            annotation_style_manager.set_label_font_family(
                ann_type, widgets["family"].currentText()
            )
            annotation_style_manager.set_label_font_size(
                ann_type, widgets["size"].value()
            )
        self.accept()
