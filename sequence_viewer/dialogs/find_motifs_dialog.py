from __future__ import annotations
from typing import Optional
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QCheckBox,QComboBox,QDialog,QDialogButtonBox,QFormLayout,QGroupBox,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QPlainTextEdit,QSpinBox,QVBoxLayout,QWidget)
from sequence_viewer.model.alignment_data_model import AlignmentDataModel
from sequence_viewer.model.annotation import Annotation, AnnotationType
from sequence_viewer.model.motif_finder import MotifFinder

_TYPE_OPTIONS = [("Primer",AnnotationType.PRIMER),("Probe",AnnotationType.PROBE)]

class FindMotifsDialog(QDialog):
    def __init__(self, model, parent=None):
        super().__init__(parent); self._model = model
        self.setWindowTitle("Find Motifs"); self.setMinimumWidth(440); self.setModal(True)
        self._build_ui(); self._connect_signals()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setSpacing(12)
        seq_group = QGroupBox("Sequence"); seq_layout = QVBoxLayout(seq_group)
        self._seq_edit = QPlainTextEdit(); self._seq_edit.setFixedHeight(72); self._seq_edit.setFont(QFont("Courier New",10))
        seq_layout.addWidget(self._seq_edit)
        self._char_count_label = QLabel("0 nt"); self._char_count_label.setAlignment(Qt.AlignRight)
        seq_layout.addWidget(self._char_count_label); root.addWidget(seq_group)
        param_group = QGroupBox("Parameters"); form = QFormLayout(param_group); form.setLabelAlignment(Qt.AlignRight)
        self._mismatch_spin = QSpinBox(); self._mismatch_spin.setRange(0,10); self._mismatch_spin.setSuffix("  mismatch(es)")
        form.addRow("Max. Mismatches:", self._mismatch_spin)
        self._name_edit = QLineEdit(); form.addRow("Annotation Name:", self._name_edit)
        self._type_combo = QComboBox()
        for dn, _ in _TYPE_OPTIONS: self._type_combo.addItem(dn)
        form.addRow("Annotation Type:", self._type_combo); root.addWidget(param_group)
        strand_group = QGroupBox("Search In"); strand_layout = QHBoxLayout(strand_group)
        self._fwd_check = QCheckBox("Forward strand (+)"); self._rev_check = QCheckBox("Reverse strand (âˆ’)")
        self._fwd_check.setChecked(True); strand_layout.addWidget(self._fwd_check)
        strand_layout.addWidget(self._rev_check); strand_layout.addStretch(); root.addWidget(strand_group)
        self._result_label = QLabel(""); self._result_label.setAlignment(Qt.AlignCenter); root.addWidget(self._result_label)
        self._buttons = QDialogButtonBox()
        self._buttons.addButton("Search", QDialogButtonBox.AcceptRole)
        self._buttons.addButton(QDialogButtonBox.Close); root.addWidget(self._buttons)

    def _connect_signals(self):
        self._seq_edit.textChanged.connect(self._on_seq_changed)
        self._buttons.accepted.connect(self._on_search); self._buttons.rejected.connect(self.reject)

    def _on_seq_changed(self):
        raw = self._seq_edit.toPlainText(); clean = raw.replace("-","").replace(" ","").replace("\n","")
        self._char_count_label.setText(f"{len(clean)} nt")

    def _on_search(self):
        query = self._seq_edit.toPlainText().replace("-","").replace(" ","").replace("\n","").strip()
        if not query: QMessageBox.warning(self,"Error","Please enter a sequence."); return
        if not self._fwd_check.isChecked() and not self._rev_check.isChecked():
            QMessageBox.warning(self,"Error","Select at least one search direction."); return
        max_mm = self._mismatch_spin.value(); name = self._name_edit.text().strip() or query[:12]
        ann_type = _TYPE_OPTIONS[self._type_combo.currentIndex()][1]

        # Row dizilerinde ara
        sequences = [self._model.get_sequence(i) for i in range(self._model.row_count())]
        finder = MotifFinder(query=query, max_mismatches=max_mm)
        hits = finder.search(sequences, search_forward=self._fwd_check.isChecked(), search_reverse=self._rev_check.isChecked())

        # Consensus dizisinde ara (aligned ise)
        consensus_hits = []
        if self._model.is_aligned:
            try:
                from sequence_viewer.model.consensus_calculator import ConsensusCalculator, ConsensusMethod
                seqs = [self._model.get_sequence(i) for i in range(self._model.row_count())]
                consensus_seq = ConsensusCalculator(ConsensusMethod.PLURALITY).compute(seqs)
                if consensus_seq:
                    consensus_finder = MotifFinder(query=query, max_mismatches=max_mm)
                    consensus_hits = consensus_finder.search(
                        [consensus_seq],
                        search_forward=self._fwd_check.isChecked(),
                        search_reverse=self._rev_check.isChecked()
                    )
            except: pass

        if not hits and not consensus_hits:
            self._result_label.setText("<span style='color:crimson'>No matches found.</span>"); return

        added = 0
        for hit in hits:
            ann = Annotation(type=ann_type, start=hit.start, end=hit.end, label=name, strand=hit.strand, notes=f"Fuzzy search: max {max_mm} mismatch(es)")
            try:
                self._model.add_annotation(hit.seq_index, ann)
                for mismatch in hit.mismatch_details:
                    marker = Annotation(
                        type=AnnotationType.MISMATCH_MARKER,
                        start=mismatch.alignment_col,
                        end=mismatch.alignment_col,
                        label=mismatch.query_base,
                        parent_id=ann.id,
                        mismatch_base=mismatch.query_base,
                        expected_base=mismatch.reference_base,
                        notes=f"Expected {mismatch.reference_base}, found {mismatch.query_base}",
                    )
                    self._model.add_annotation(hit.seq_index, marker)
                added += 1
            except: pass

        consensus_added = 0
        for hit in consensus_hits:
            ann = Annotation(type=ann_type, start=hit.start, end=hit.end, label=name, strand=hit.strand, notes=f"Fuzzy search (consensus): max {max_mm} mismatch(es)")
            try:
                self._model.add_consensus_annotation(ann)
                for mismatch in hit.mismatch_details:
                    marker = Annotation(
                        type=AnnotationType.MISMATCH_MARKER,
                        start=mismatch.alignment_col,
                        end=mismatch.alignment_col,
                        label=mismatch.query_base,
                        parent_id=ann.id,
                        mismatch_base=mismatch.query_base,
                        expected_base=mismatch.reference_base,
                        notes=f"Expected {mismatch.reference_base}, found {mismatch.query_base}",
                    )
                    self._model.add_consensus_annotation(marker)
                consensus_added += 1
            except: pass

        msg = f"<span style='color:green'>{len(hits)} match(es) in sequences ({added} added)"
        if self._model.is_aligned:
            msg += f", {len(consensus_hits)} in consensus ({consensus_added} added)"
        msg += ".</span>"
        self._result_label.setText(msg)


