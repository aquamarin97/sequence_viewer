# main.py

import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from model.annotation import Annotation, AnnotationType
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
        print(f"Hata: Klasör bulunamadı veya geçersiz - {directory_path}")
        return []

    exts = {".fasta", ".fa", ".fna", ".ffn", ".faa", ".frn"}
    files = sorted({p for p in directory.iterdir() if p.suffix.lower() in exts})
    return files


def main():
    app = QApplication(sys.argv)

    workspace = SequenceWorkspaceWidget()
    workspace.setWindowTitle("MSA Viewer")
    workspace.resize(1200, 500)

    # FASTA yükle → modele ekle → workspace otomatik güncellenir
    print(f"FASTA taranıyor: {TARGETDIRECTORY}")
    fasta_files = find_fasta_files(TARGETDIRECTORY)

    if not fasta_files:
        print("Hiç FASTA dosyası bulunamadı.")
        return 1

    print(f"{len(fasta_files)} dosya bulundu.")
    sequences = load_fasta_files([str(p) for p in fasta_files])

    if not sequences:
        print("Hata: Hiç sekans yüklenemedi.")
        return 1

    print(f"\nToplam {len(sequences)} sekans yükleniyor...")

    # Tek giriş noktası: workspace.add_sequence()
    # Bu; model → sinyal → view zincirini tetikler.
    for header, sequence in sequences:
        workspace.add_sequence(header, sequence)

    # İstatistik
    lengths = [len(seq) for _, seq in sequences]
    print(f"Uzunluk: min={min(lengths)}, max={max(lengths)}, "
          f"ort={sum(lengths)/len(lengths):.0f}")
    workspace.add_annotation(Annotation(
        type=AnnotationType.REGION,
        start=50, end=72,
        label="FP-1",
        strand="+",
        tm=62.4,
        gc_percent=52.1,
        notes="16S universal forward primer",
    ))
    workspace.show()
    return app.exec_()
    # FORWARD_PRIMER = auto()
    # REVERSE_PRIMER = auto()
    # PROBE          = auto()
    # REGION         = auto()

if __name__ == "__main__":
    sys.exit(main())