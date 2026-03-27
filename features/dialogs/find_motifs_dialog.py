# features/dialogs/find_motifs_dialog.py

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit,
    QVBoxLayout, QWidget,
)

from model.annotation import Annotation, AnnotationType
from model.annotation_store import AnnotationStore
from model.motif_finder import MotifFinder

_TYPE_OPTIONS = [
    ("Forward Primer", AnnotationType.FORWARD_PRIMER),
    ("Reverse Primer", AnnotationType.REVERSE_PRIMER),
    ("Probe",          AnnotationType.PROBE),
    ("Region",         AnnotationType.REGION),
]


class FindMotifsDialog(QDialog):

    def __init__(
        self,
        store: AnnotationStore,
        sequences: List[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._store     = store
        self._sequences = sequences
        self.setWindowTitle("Find Motifs")
        self.setMinimumWidth(440)
        self.setModal(True)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # Sequence girişi
        seq_group = QGroupBox("Sequence")
        seq_layout = QVBoxLayout(seq_group)
        self._seq_edit = QPlainTextEdit()
        self._seq_edit.setPlaceholderText(
            "Motif / primer / probe dizisini girin…\n"
            "Boşluk ve tire (-) karakterleri yoksayılır."
        )
        self._seq_edit.setFixedHeight(72)
        self._seq_edit.setFont(QFont("Courier New", 10))
        seq_layout.addWidget(self._seq_edit)
        self._char_count_label = QLabel("0 nt")
        self._char_count_label.setAlignment(Qt.AlignRight)
        seq_layout.addWidget(self._char_count_label)
        root.addWidget(seq_group)

        # Parametreler
        from PyQt5.QtWidgets import QSpinBox
        param_group = QGroupBox("Parameters")
        form = QFormLayout(param_group)
        form.setLabelAlignment(Qt.AlignRight)

        self._mismatch_spin = QSpinBox()
        self._mismatch_spin.setRange(0, 10)
        self._mismatch_spin.setValue(0)
        self._mismatch_spin.setSuffix("  mismatch(es)")
        form.addRow("Max. Mismatches:", self._mismatch_spin)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("örn. FP-1, Probe-TaqMan…")
        form.addRow("Annotation Name:", self._name_edit)

        self._type_combo = QComboBox()
        for display_name, _ in _TYPE_OPTIONS:
            self._type_combo.addItem(display_name)
        form.addRow("Annotation Type:", self._type_combo)

        root.addWidget(param_group)

        # Arama yönü
        strand_group = QGroupBox("Search In")
        strand_layout = QHBoxLayout(strand_group)
        self._fwd_check = QCheckBox("Forward strand  (+)")
        self._rev_check = QCheckBox("Reverse strand  (−)")
        self._fwd_check.setChecked(True)
        strand_layout.addWidget(self._fwd_check)
        strand_layout.addWidget(self._rev_check)
        strand_layout.addStretch()
        root.addWidget(strand_group)

        self._result_label = QLabel("")
        self._result_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self._result_label)

        self._buttons = QDialogButtonBox()
        self._search_btn = self._buttons.addButton("Search", QDialogButtonBox.AcceptRole)
        self._buttons.addButton(QDialogButtonBox.Close)
        root.addWidget(self._buttons)

    def _connect_signals(self) -> None:
        self._seq_edit.textChanged.connect(self._on_seq_changed)
        self._buttons.accepted.connect(self._on_search)
        self._buttons.rejected.connect(self.reject)

    def _on_seq_changed(self) -> None:
        raw   = self._seq_edit.toPlainText()
        clean = raw.replace("-", "").replace(" ", "").replace("\n", "")
        self._char_count_label.setText(f"{len(clean)} nt")

    def _on_search(self) -> None:
        query = (self._seq_edit.toPlainText()
                 .replace("-", "").replace(" ", "").replace("\n", "").strip())
        if not query:
            QMessageBox.warning(self, "Hata", "Lütfen bir dizi girin.")
            return
        if not self._fwd_check.isChecked() and not self._rev_check.isChecked():
            QMessageBox.warning(self, "Hata", "En az bir arama yönü seçin.")
            return

        max_mm   = self._mismatch_spin.value()
        name     = self._name_edit.text().strip() or query[:12]
        ann_type = _TYPE_OPTIONS[self._type_combo.currentIndex()][1]

        finder = MotifFinder(query=query, max_mismatches=max_mm)
        hits   = finder.search(
            self._sequences,
            search_forward=self._fwd_check.isChecked(),
            search_reverse=self._rev_check.isChecked(),
        )

        if not hits:
            self._result_label.setText(
                "<span style='color:crimson'>Eşleşme bulunamadı.</span>"
            )
            return

        # Pozisyon bazında grupla: {(start, end, strand): [seq_index, ...]}
        groups: Dict[tuple, List[int]] = {}
        for hit in hits:
            key = (hit.start, hit.end, hit.strand)
            groups.setdefault(key, []).append(hit.seq_index)

        added = 0
        for (start, end, strand), seq_indices in groups.items():
            # Strand'a göre tip override
            effective_type = ann_type
            if strand == "-" and ann_type == AnnotationType.FORWARD_PRIMER:
                effective_type = AnnotationType.REVERSE_PRIMER
            elif strand == "+" and ann_type == AnnotationType.REVERSE_PRIMER:
                effective_type = AnnotationType.FORWARD_PRIMER

            ann = Annotation(
                type        = effective_type,
                start       = start,
                end         = end,
                label       = name,
                strand      = strand,
                notes       = f"Fuzzy search: max {max_mm} mismatch(es)",
                # Her annotasyon sadece eşleşen satırlarda görünür
                seq_indices = sorted(seq_indices),
            )
            self._store.add(ann)
            added += 1

        total_hits = len(hits)
        self._result_label.setText(
            f"<span style='color:green'>"
            f"{total_hits} eşleşme bulundu, {added} annotasyon eklendi."
            f"</span>"
        )