from __future__ import annotations
from typing import Optional
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QColorDialog,QComboBox,QDialog,QDialogButtonBox,QDoubleSpinBox,QFormLayout,QFrame,QGroupBox,QHBoxLayout,QLabel,QLineEdit,QPushButton,QRadioButton,QSpinBox,QTextEdit,QVBoxLayout,QWidget)
from sequence_viewer.model.annotation import Annotation, AnnotationType

_TYPE_OPTIONS = [("Primer",AnnotationType.PRIMER),("Probe",AnnotationType.PROBE),("Repeated Region",AnnotationType.REPEATED_REGION)]

class EditAnnotationDialog(QDialog):
    def __init__(self, annotation, parent=None):
        super().__init__(parent); self._annotation = annotation; self._result = None
        self._current_color = annotation.resolved_color()
        self.setWindowTitle("Edit Annotation"); self.setMinimumWidth(440); self.setModal(True)
        self._build_ui(); self._populate(annotation); self._connect_signals(); self._update_strand_visibility()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setSpacing(10)
        general = QGroupBox("General"); form_g = QFormLayout(general); form_g.setLabelAlignment(Qt.AlignRight)
        self._name_edit = QLineEdit(); form_g.addRow("Name:", self._name_edit)
        self._type_combo = QComboBox()
        for display, _ in _TYPE_OPTIONS: self._type_combo.addItem(display)
        form_g.addRow("Type:", self._type_combo)
        self._strand_widget = QWidget(); sl = QHBoxLayout(self._strand_widget); sl.setContentsMargins(0,0,0,0)
        self._fwd_radio = QRadioButton("Forward (+)"); self._rev_radio = QRadioButton("Reverse (âˆ’)")
        sl.addWidget(self._fwd_radio); sl.addWidget(self._rev_radio); sl.addStretch()
        self._strand_label = QLabel("Direction:"); form_g.addRow(self._strand_label, self._strand_widget)
        pos_widget = QWidget(); pl = QHBoxLayout(pos_widget); pl.setContentsMargins(0,0,0,0)
        self._start_spin = QSpinBox(); self._start_spin.setRange(1, 9_999_999)
        self._end_spin = QSpinBox(); self._end_spin.setRange(1, 9_999_999)
        pl.addWidget(self._start_spin); pl.addWidget(QLabel(" to ")); pl.addWidget(self._end_spin); pl.addStretch()
        form_g.addRow("Binding Site:", pos_widget); root.addWidget(general)
        prop = QGroupBox("Properties"); form_p = QFormLayout(prop); form_p.setLabelAlignment(Qt.AlignRight)
        color_w = QWidget(); cl = QHBoxLayout(color_w); cl.setContentsMargins(0,0,0,0)
        self._color_preview = QLabel(); self._color_preview.setFrameStyle(QFrame.Box); self._color_preview.setFixedSize(28,22)
        self._color_btn = QPushButton("Chooseâ€¦"); self._color_btn.setFixedSize(72,22)
        cl.addWidget(self._color_preview); cl.addWidget(self._color_btn); cl.addStretch()
        form_p.addRow("Color:", color_w)
        self._identity_spin = QDoubleSpinBox(); self._identity_spin.setRange(0.0,100.0); self._identity_spin.setSuffix(" %"); self._identity_spin.setDecimals(1)
        form_p.addRow("% Identity:", self._identity_spin)
        self._score_spin = QDoubleSpinBox(); self._score_spin.setRange(-9999.0,9999.0); self._score_spin.setDecimals(3)
        self._score_spin.setSpecialValueText("â€”"); self._score_spin.setValue(-9999.0)
        form_p.addRow("Score:", self._score_spin)
        self._notes_edit = QTextEdit(); self._notes_edit.setFixedHeight(54); form_p.addRow("Notes:", self._notes_edit)
        root.addWidget(prop)
        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); root.addWidget(self._buttons)

    def _populate(self, ann):
        self._name_edit.setText(ann.label)
        for i, (_,t) in enumerate(_TYPE_OPTIONS):
            if t == ann.type: self._type_combo.setCurrentIndex(i); break
        if ann.strand == "-": self._rev_radio.setChecked(True)
        else: self._fwd_radio.setChecked(True)
        self._start_spin.setValue(ann.start+1); self._end_spin.setValue(ann.end+1)
        self._update_color_preview()
        if ann.score is not None: self._score_spin.setValue(ann.score)
        self._notes_edit.setPlainText(ann.notes)

    def _connect_signals(self):
        self._type_combo.currentIndexChanged.connect(self._update_strand_visibility)
        self._color_btn.clicked.connect(self._choose_color)
        self._buttons.accepted.connect(self._on_ok); self._buttons.rejected.connect(self.reject)

    def _update_strand_visibility(self):
        _, ann_type = _TYPE_OPTIONS[self._type_combo.currentIndex()]
        show = ann_type.uses_strand()
        self._strand_label.setVisible(show); self._strand_widget.setVisible(show)

    def _choose_color(self):
        color = QColorDialog.getColor(self._current_color, self, "Choose Color")
        if color.isValid(): self._current_color = color; self._update_color_preview()

    def _update_color_preview(self):
        c = self._current_color
        self._color_preview.setStyleSheet(f"background-color:rgb({c.red()},{c.green()},{c.blue()});border:1px solid #888;")

    def _on_ok(self):
        _, ann_type = _TYPE_OPTIONS[self._type_combo.currentIndex()]
        strand = "-" if self._rev_radio.isChecked() else "+"
        score_val = self._score_spin.value(); score = None if score_val <= -9999.0 else score_val
        self._result = Annotation(id=self._annotation.id, type=ann_type, start=self._start_spin.value()-1, end=self._end_spin.value()-1,
            label=self._name_edit.text().strip() or self._annotation.label, strand=strand, color=QColor(self._current_color),
            score=score, tm=self._annotation.tm, gc_percent=self._annotation.gc_percent, notes=self._notes_edit.toPlainText().strip())
        self.accept()

    def result_annotation(self): return self._result


