# main.py

import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QMenu

from widgets.workspace import SequenceWorkspaceWidget


TARGETDIRECTORY = r"test_alignment"


def load_fasta_files(fasta_paths):
    try:
        from Bio import SeqIO
    except ImportError:
        print("BioPython kurulu değil! 'pip install biopython' ile kurun.")
        return []

    sequences = []
    for fasta_path in fasta_paths:
        path = Path(fasta_path)
        if not path.exists():
            print(f"Uyarı: Dosya bulunamadı - {fasta_path}")
            continue
        try:
            print(f"FASTA okunuyor: {path.name}")
            count = 0
            for record in SeqIO.parse(str(path), "fasta"):
                sequences.append((record.description, str(record.seq).upper()))
                count += 1
            print(f"  → {count} sekans yüklendi")
        except Exception as e:
            print(f"Hata ({path.name}): {e}")
    return sequences


def find_fasta_files(directory_path):
    directory = Path(directory_path)
    if not directory.exists() or not directory.is_dir():
        print(f"Hata: Klasör bulunamadı - {directory_path}")
        return []
    exts  = {".fasta", ".fa", ".fna", ".ffn", ".faa", ".frn"}
    files = sorted({p for p in directory.iterdir() if p.suffix.lower() in exts})
    return files


class MainWindow(QMainWindow):
    def __init__(self, workspace: SequenceWorkspaceWidget) -> None:
        super().__init__()
        self.workspace = workspace
        self.setWindowTitle("MSA Viewer")
        self.setCentralWidget(workspace)
        self._build_menu()

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        # ---- Annotate menüsü ----
        annotate_menu: QMenu = menubar.addMenu("Annotate")

        find_motifs_action = QAction("Find Motifs…", self)
        find_motifs_action.setShortcut("Ctrl+F")
        find_motifs_action.triggered.connect(self.workspace.open_find_motifs_dialog)
        annotate_menu.addAction(find_motifs_action)

        annotate_menu.addSeparator()

        clear_ann_action = QAction("Clear All Annotations", self)
        clear_ann_action.triggered.connect(self.workspace.clear_annotations)
        annotate_menu.addAction(clear_ann_action)

        # ---- View menüsü (placeholder) ----
        view_menu: QMenu = menubar.addMenu("View")

        toggle_dark_action = QAction("Toggle Dark Mode", self)
        toggle_dark_action.setShortcut("Ctrl+D")
        toggle_dark_action.triggered.connect(self._toggle_dark_mode)
        view_menu.addAction(toggle_dark_action)

    def _toggle_dark_mode(self) -> None:
        from settings.theme import theme_manager
        theme_manager.toggle()


def main():
    app = QApplication(sys.argv)

    workspace = SequenceWorkspaceWidget()
    workspace.resize(1200, 600)

    window = MainWindow(workspace)
    window.resize(1200, 650)

    # FASTA yükle
    print(f"FASTA taranıyor: {TARGETDIRECTORY}")
    fasta_files = find_fasta_files(TARGETDIRECTORY)

    if not fasta_files:
        print("Hiç FASTA dosyası bulunamadı.")
    else:
        print(f"{len(fasta_files)} dosya bulundu.")
        sequences = load_fasta_files([str(p) for p in fasta_files])

        if not sequences:
            print("Hiç sekans yüklenemedi.")
        else:
            print(f"\nToplam {len(sequences)} sekans yükleniyor...")
            for header, sequence in sequences:
                workspace.add_sequence(header, sequence)

            lengths = [len(seq) for _, seq in sequences]
            print(
                f"Uzunluk: min={min(lengths)}, max={max(lengths)}, "
                f"ort={sum(lengths)/len(lengths):.0f}"
            )

    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())