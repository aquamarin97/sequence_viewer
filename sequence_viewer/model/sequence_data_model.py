# sequence_viewer/model/sequence_data_model.py
# model/sequence_data_model.py
from typing import List, Tuple

class SequenceDataModel:
    def __init__(self):
        self.sequences: List[Tuple[str, str]] = []

    def load_fasta(self, file_path):
        self.sequences.clear()
        header = None
        seq_chunks = []
        with open(file_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line: continue
                if line.startswith(">"):
                    if header is not None:
                        self.sequences.append((header, "".join(seq_chunks)))
                    header = line[1:].strip()
                    seq_chunks = []
                else:
                    seq_chunks.append(line)
        if header is not None:
            self.sequences.append((header, "".join(seq_chunks)))

    def add_sequence(self, header, sequence):
        self.sequences.append((header, sequence))


