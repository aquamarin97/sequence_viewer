# msa_viewer/model/sequence_data_model.py

from typing import List, Tuple


class SequenceDataModel:
    """
    SequenceDataModel, sekans verilerini saklayan ve FASTA dosyalarından
    yükleyen basit veri modelidir.
    """

    def __init__(self) -> None:
        self.sequences: List[Tuple[str, str]] = []

    def load_fasta(self, file_path: str) -> None:
        """
        Verilen FASTA dosyasını okuyup başlık-sekans çiftlerini kaydeder.
        """
        self.sequences.clear()
        header = None
        seq_chunks: List[str] = []

        with open(file_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                if line.startswith(">"):
                    # önceki sekansı kaydet
                    if header is not None:
                        sequence = "".join(seq_chunks)
                        self.sequences.append((header, sequence))
                    header = line[1:].strip()
                    seq_chunks = []
                else:
                    seq_chunks.append(line)

        # son sekansı ekle
        if header is not None:
            sequence = "".join(seq_chunks)
            self.sequences.append((header, sequence))

    def add_sequence(self, header: str, sequence: str) -> None:
        """
        Manuel olarak bir sekans ekler.
        """
        self.sequences.append((header, sequence))
