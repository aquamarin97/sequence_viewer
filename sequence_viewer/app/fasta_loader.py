# sequence_viewer/app/fasta_loader.py
from pathlib import Path


def load_fasta_files(fasta_paths):
    try:
        from Bio import SeqIO
    except ImportError:
        print("BioPython kurulu degil! 'pip install biopython' ile kurun.")
        return []

    sequences = []
    for fasta_path in fasta_paths:
        path = Path(fasta_path)
        if not path.exists():
            continue
        try:
            print(f"FASTA okunuyor: {path.name}")
            count = 0
            for record in SeqIO.parse(str(path), "fasta"):
                sequences.append((record.description, str(record.seq).upper()))
                count += 1
            print(f"  -> {count} sekans yuklendi")
        except Exception as exc:
            print(f"Hata ({path.name}): {exc}")
    return sequences


