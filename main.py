# main.py

import sys
import os
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from model.sequence_data_model import SequenceDataModel
from widgets.workspace import SequenceWorkspaceWidget


TARGETDIRECTORY = r"C:\Users\gül\Desktop\CMV\RepeatedSequenceFinder_R3-hiv\inputs\test"

def load_fasta_files(fasta_paths):
    """
    BioPython kullanarak FASTA dosyalarını yükler ve sequence/header bilgilerini döndürür.
    
    Args:
        fasta_paths: FASTA dosya path'lerinin listesi
        
    Returns:
        List of tuples: [(header, sequence), ...]
    """
    try:
        from Bio import SeqIO
    except ImportError:
        print("BioPython kurulu değil! Lütfen 'pip install biopython' komutu ile kurun.")
        return []
    
    sequences = []
    
    for fasta_path in fasta_paths:
        path = Path(fasta_path)
        if not path.exists():
            print(f"Uyarı: Dosya bulunamadı - {fasta_path}")
            continue
            
        try:
            print(f"FASTA dosyası okunuyor: {path.name}")
            record_count = 0
            
            for record in SeqIO.parse(str(path), "fasta"):
                header = record.description
                sequence = str(record.seq)
                
                # Sequence'i uppercase'e çevir
                sequence = sequence.upper()
                
                sequences.append((header, sequence))
                record_count += 1
                
            print(f"  - {record_count} sequence yüklendi")
                
        except Exception as e:
            print(f"Hata: {path} dosyası okunurken hata oluştu: {e}")
    
    return sequences

def find_fasta_files(directory_path):
    """
    Belirtilen klasördeki tüm FASTA dosyalarını bulur.
    
    Args:
        directory_path: Klasör path'i
        
    Returns:
        List of Path: FASTA dosya path'lerinin listesi
    """
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"Hata: Klasör bulunamadı - {directory_path}")
        return []
    
    if not directory.is_dir():
        print(f"Hata: Bu bir klasör değil - {directory_path}")
        return []
    
    # Tüm FASTA dosya uzantılarını ara
    fasta_extensions = ['.fasta', '.fa', '.fna', '.ffn', '.faa', '.frn']
    fasta_files = []
    
    for ext in fasta_extensions:
        fasta_files.extend(directory.glob(f'*{ext}'))
        fasta_files.extend(directory.glob(f'*{ext.upper()}'))
    
    # Alt klasörlerde de ara (opsiyonel)
    # for ext in fasta_extensions:
    #     fasta_files.extend(directory.rglob(f'*{ext}'))
    #     fasta_files.extend(directory.rglob(f'*{ext.upper()}'))
    
    # Tekilleştir ve sırala
    fasta_files = list(set(fasta_files))
    fasta_files.sort()
    
    return fasta_files

def get_fasta_paths():
    """
    Klasördeki tüm FASTA dosyalarını bulur.
    """
    # Belirttiğiniz klasör path'i
    target_directory = TARGETDIRECTORY
    
    print(f"FASTA dosyaları aranıyor: {target_directory}")
    fasta_files = find_fasta_files(target_directory)
    
    if not fasta_files:
        print("Hiç FASTA dosyası bulunamadı!")
        print("Desteklenen uzantılar: .fasta, .fa, .fna, .ffn, .faa, .frn")
        return []
    
    print(f"Bulunan FASTA dosyaları ({len(fasta_files)} adet):")
    for i, fasta_file in enumerate(fasta_files, 1):
        print(f"  {i}. {fasta_file.name}")
    
    return [str(path) for path in fasta_files]

def main():
    app = QApplication(sys.argv)

    # Ana pencereyi oluştur
    viewer = SequenceWorkspaceWidget()
    viewer.setWindowTitle("MSA Viewer - FASTA Folder Loader")
    viewer.resize(1200, 500)

    # Modeli oluştur
    model = SequenceDataModel()
    
    # FASTA dosyalarını yükle
    print("FASTA dosyaları yükleniyor...")
    fasta_paths = get_fasta_paths()
    
    if not fasta_paths:
        print("Hiç FASTA dosyası bulunamadı. Program kapatılıyor.")
        return 1
    
    sequences_data = load_fasta_files(fasta_paths)
    
    if not sequences_data:
        print("Hata: Hiç sequence yüklenemedi. Program kapatılıyor.")
        return 1
    
    print(f"\nToplam {len(sequences_data)} sequence yüklendi.")
    
    # Sequence'leri modele ekle
    for header, sequence in sequences_data:
        model.add_sequence(header, sequence)
    
    # Sequence'leri viewer'a yükle
    for header, seq in model.sequences:
        viewer.add_sequence(header, seq)
    
    # İstatistikleri göster
    total_sequences = len(model.sequences)
    if total_sequences > 0:
        seq_lengths = [len(seq) for _, seq in model.sequences]
        avg_length = sum(seq_lengths) / total_sequences
        max_length = max(seq_lengths)
        min_length = min(seq_lengths)
    
    viewer.show()
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())