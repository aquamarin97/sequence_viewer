# features/dialogs/edit_annotation_dialog.py
"""
Edit Annotation diyaloğu.

Açılış: annotasyon çift tıklaması ile.
Dinamik: AnnotationType'a göre Primer-specific alanlar gösterilir/gizlenir.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QColorDialog, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QRadioButton, QSpinBox, QTextEdit, QVBoxLayout,
    QWidget,
)

from model.annotation import Annotation, AnnotationType


_TYPE_OPTIONS = [
    ("Forward Primer", AnnotationType.FORWARD_PRIMER),
    ("Reverse Primer", AnnotationType.REVERSE_PRIMER),
    ("Probe",          AnnotationType.PROBE),
    ("Region",         AnnotationType.REGION),
]

_PRIMER_TYPES = {AnnotationType.FORWARD_PRIMER, AnnotationType.REVERSE_PRIMER}


class EditAnnotationDialog(QDialog):
    """
    Annotasyon düzenleme diyaloğu.

    result_annotation() → güncellenmiş Annotation veya None (iptal).
    """

    def __init__(
        self,
        annotation: Annotation,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._annotation   = annotation
        self._result:       Optional[Annotation] = None
        self._current_color: QColor = annotation.resolved_color()

        self.setWindowTitle("Edit Annotation")
        self.setMinimumWidth(460)
        self.setModal(True)

        self._build_ui()
        self._populate(annotation)
        self._connect_signals()
        self._update_primer_fields_visibility()

    # ------------------------------------------------------------------
    # UI kurulumu
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ---- Genel bilgiler ----
        general_group = QGroupBox("General")
        form_g = QFormLayout(general_group)
        form_g.setLabelAlignment(Qt.AlignRight)

        self._name_edit = QLineEdit()
        form_g.addRow("Name:", self._name_edit)

        self._type_combo = QComboBox()
        for display, _ in _TYPE_OPTIONS:
            self._type_combo.addItem(display)
        form_g.addRow("Type:", self._type_combo)

        # Direction (sadece primerler için)
        self._direction_widget = QWidget()
        dir_layout = QHBoxLayout(self._direction_widget)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        self._fwd_radio = QRadioButton("Forward  (+)")
        self._rev_radio = QRadioButton("Reverse  (−)")
        dir_layout.addWidget(self._fwd_radio)
        dir_layout.addWidget(self._rev_radio)
        dir_layout.addStretch()
        self._direction_label = QLabel("Direction:")
        form_g.addRow(self._direction_label, self._direction_widget)

        # Binding site
        self._binding_widget = QWidget()
        bs_layout = QHBoxLayout(self._binding_widget)
        bs_layout.setContentsMargins(0, 0, 0, 0)
        self._start_spin = QSpinBox(); self._start_spin.setRange(1, 9_999_999)
        self._end_spin   = QSpinBox(); self._end_spin.setRange(1, 9_999_999)
        bs_layout.addWidget(self._start_spin)
        bs_layout.addWidget(QLabel(" to "))
        bs_layout.addWidget(self._end_spin)
        bs_layout.addStretch()
        form_g.addRow("Binding Site:", self._binding_widget)

        root.addWidget(general_group)

        # ---- Characteristics (Primer-only) ----
        self._char_group = QGroupBox("Characteristics")
        form_c = QFormLayout(self._char_group)
        form_c.setLabelAlignment(Qt.AlignRight)

        def _placeholder_field(placeholder: str) -> QLineEdit:
            f = QLineEdit()
            f.setPlaceholderText(placeholder)
            f.setReadOnly(True)   # backend yok — sadece UI
            f.setStyleSheet("color: gray;")
            return f

        self._tm_field       = _placeholder_field("Tm (°C) — hesaplanacak")
        self._gc_field       = _placeholder_field("%GC — hesaplanacak")
        self._hairpin_field  = _placeholder_field("Hairpin Tm — hesaplanacak")
        self._dimer_field    = _placeholder_field("Self Dimer Tm — hesaplanacak")
        self._length_field   = _placeholder_field("Length (bp)")

        form_c.addRow("Length:",     self._length_field)
        form_c.addRow("Tm:",         self._tm_field)
        form_c.addRow("%GC:",        self._gc_field)
        form_c.addRow("Hairpin Tm:", self._hairpin_field)
        form_c.addRow("Self Dimer:", self._dimer_field)

        root.addWidget(self._char_group)

        # ---- Properties ----
        prop_group = QGroupBox("Properties")
        form_p = QFormLayout(prop_group)
        form_p.setLabelAlignment(Qt.AlignRight)

        # Renk seçici
        color_widget = QWidget()
        color_layout = QHBoxLayout(color_widget)
        color_layout.setContentsMargins(0, 0, 0, 0)
        self._color_btn      = QPushButton()
        self._color_btn.setFixedSize(28, 22)
        self._color_preview  = QLabel()
        self._color_preview.setFrameStyle(QFrame.Box)
        self._color_preview.setFixedSize(28, 22)
        color_layout.addWidget(self._color_preview)
        color_layout.addWidget(self._color_btn)
        color_layout.addStretch()
        self._color_btn.setText("Choose…")
        form_p.addRow("Color:", color_widget)

        # % Identity
        self._identity_spin = QDoubleSpinBox()
        self._identity_spin.setRange(0.0, 100.0)
        self._identity_spin.setSuffix(" %")
        self._identity_spin.setDecimals(1)
        form_p.addRow("% Identity:", self._identity_spin)

        # Motif (hedef dizi)
        self._motif_edit = QLineEdit()
        self._motif_edit.setPlaceholderText(
            "Bağlanılan bölgedeki hedef dizi…"
        )
        form_p.addRow("Motif:", self._motif_edit)

        # Score
        self._score_spin = QDoubleSpinBox()
        self._score_spin.setRange(-9999.0, 9999.0)
        self._score_spin.setDecimals(3)
        self._score_spin.setSpecialValueText("—")
        self._score_spin.setValue(-9999.0)
        form_p.addRow("Score:", self._score_spin)

        # Notes
        self._notes_edit = QTextEdit()
        self._notes_edit.setFixedHeight(54)
        form_p.addRow("Notes:", self._notes_edit)

        root.addWidget(prop_group)

        # ---- Dialog buttons ----
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        root.addWidget(self._buttons)

    def _populate(self, ann: Annotation) -> None:
        """Mevcut annotasyon verisiyle alanları doldur."""
        self._name_edit.setText(ann.label)

        # Type combo
        for i, (_, t) in enumerate(_TYPE_OPTIONS):
            if t == ann.type:
                self._type_combo.setCurrentIndex(i)
                break

        # Direction
        if ann.strand == "-":
            self._rev_radio.setChecked(True)
        else:
            self._fwd_radio.setChecked(True)

        # Binding site (1-based gösterim)
        self._start_spin.setValue(ann.start + 1)
        self._end_spin.setValue(ann.end   + 1)

        # Characteristics (read-only placeholder'lar)
        length = ann.length()
        self._length_field.setPlaceholderText(f"{length} bp")
        if ann.tm is not None:
            self._tm_field.setPlaceholderText(f"{ann.tm:.1f} °C")
        if ann.gc_percent is not None:
            self._gc_field.setPlaceholderText(f"{ann.gc_percent:.1f} %")

        # Color preview
        self._update_color_preview()

        # Score
        if ann.score is not None:
            self._score_spin.setValue(ann.score)

        # Notes
        self._notes_edit.setPlainText(ann.notes)

    def _connect_signals(self) -> None:
        self._type_combo.currentIndexChanged.connect(
            self._update_primer_fields_visibility
        )
        self._color_btn.clicked.connect(self._choose_color)
        self._buttons.accepted.connect(self._on_ok)
        self._buttons.rejected.connect(self.reject)
        self._start_spin.valueChanged.connect(self._update_length_preview)
        self._end_spin.valueChanged.connect(self._update_length_preview)

    # ------------------------------------------------------------------
    # Dinamik görünürlük
    # ------------------------------------------------------------------

    def _update_primer_fields_visibility(self) -> None:
        _, ann_type = _TYPE_OPTIONS[self._type_combo.currentIndex()]
        is_primer = ann_type in _PRIMER_TYPES

        self._direction_label.setVisible(is_primer)
        self._direction_widget.setVisible(is_primer)
        self._char_group.setVisible(is_primer)

    # ------------------------------------------------------------------
    # Renk
    # ------------------------------------------------------------------

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(self._current_color, self, "Choose Color")
        if color.isValid():
            self._current_color = color
            self._update_color_preview()

    def _update_color_preview(self) -> None:
        c = self._current_color
        self._color_preview.setStyleSheet(
            f"background-color: rgb({c.red()},{c.green()},{c.blue()});"
            f"border: 1px solid #888;"
        )

    # ------------------------------------------------------------------
    # Length preview
    # ------------------------------------------------------------------

    def _update_length_preview(self) -> None:
        length = max(0, self._end_spin.value() - self._start_spin.value() + 1)
        self._length_field.setPlaceholderText(f"{length} bp")

    # ------------------------------------------------------------------
    # OK
    # ------------------------------------------------------------------

    def _on_ok(self) -> None:
        _, ann_type = _TYPE_OPTIONS[self._type_combo.currentIndex()]
        strand = "-" if self._rev_radio.isChecked() else "+"

        score_val = self._score_spin.value()
        score = None if score_val <= -9999.0 else score_val

        self._result = Annotation(
            id      = self._annotation.id,          # aynı id — store.update() için
            type    = ann_type,
            start   = self._start_spin.value() - 1,  # 0-based
            end     = self._end_spin.value()   - 1,
            label   = self._name_edit.text().strip() or self._annotation.label,
            strand  = strand,
            color   = QColor(self._current_color),
            score   = score,
            tm      = self._annotation.tm,
            gc_percent = self._annotation.gc_percent,
            notes   = self._notes_edit.toPlainText().strip(),
        )
        self.accept()

    # ------------------------------------------------------------------
    # Sonuç
    # ------------------------------------------------------------------

    def result_annotation(self) -> Optional[Annotation]:
        return self._result