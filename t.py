#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mojibake Fixer - Python dosyalarındaki karakter kodlama bozukluklarını düzelt
"""

import os
import re
from pathlib import Path

def detect_encoding(file_path):
    """Dosyanın kodlamasını basit yöntemle tahmin et"""
    try:
        # Önce UTF-8 dene
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read()
            return 'utf-8', 1.0
    except UnicodeDecodeError:
        pass
    
    # Diğer yaygın encodingler
    encodings = ['latin1', 'cp1254', 'iso-8859-9', 'windows-1254']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read()
                return enc, 0.8
        except:
            continue
    
    return 'utf-8', 0.5

def fix_mojibake_patterns(text):
    """Yaygın Mojibake desenlerini düzelt"""
    changes = 0
    fixed_text = text
    
    # 1. BOM (Byte Order Mark) karakterlerini temizle
    bom_chars = [
        '\ufeff',  # UTF-8 BOM
        '\ufffe',  # UTF-16 BOM (LE)
        '\u0000feff',  # UTF-32 BOM
    ]
    for bom in bom_chars:
        if bom in fixed_text:
            fixed_text = fixed_text.replace(bom, '')
            changes += 1
    
    # 2. Satır başındaki ve ortasındaki görünmez BOM'ları temizle
    lines = fixed_text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Her satırın başındaki BOM'u temizle
        cleaned_line = line.lstrip('\ufeff\ufffe')
        if cleaned_line != line:
            changes += 1
        cleaned_lines.append(cleaned_line)
    fixed_text = '\n'.join(cleaned_lines)
    
    # 3. Türkçe karakter düzeltmeleri (UTF-8 karakterlerin Latin-1 olarak yorumlanması)
    mojibake_map = {
        'Ã§': 'ç', 'Ã‡': 'Ç',
        'Ä±': 'ı', 'Ä°': 'İ',
        'Ã¶': 'ö', 'Ã–': 'Ö',
        'Ã¼': 'ü', 'Ãœ': 'Ü',
        'ÅŸ': 'ş', 'Åž': 'Ş',
        'Ä\x9f': 'ğ', 'Ä\x9e': 'Ğ',
        'Ä°': 'ğ', 'Ä': 'Ğ',
        # İngilizce tipografik karakterler
        'â€™': "'", 'â€œ': '"', 'â€\x9d': '"',
        'â€"': '—', 'â€"': '–',
        'â€¦': '…',
        # Diğer yaygın hatalar
        'Ã¢': 'â', 'Ã©': 'é', 'Ã¨': 'è',
        'Ã¡': 'á', 'Ã ': 'à',
        'Ã³': 'ó', 'Ã²': 'ò',
        'Ãº': 'ú', 'Ã¹': 'ù',
    }
    
    for wrong, correct in mojibake_map.items():
        if wrong in fixed_text:
            fixed_text = fixed_text.replace(wrong, correct)
            changes += 1
    
    # 4. Yinelenen yorumları kaldır (aynı satır art arda)
    lines = fixed_text.split('\n')
    deduplicated_lines = []
    prev_line = None
    for line in lines:
        # Eğer satır bir yorum satırı ise ve bir öncekiyle aynıysa atla
        if line.strip().startswith('#') and line == prev_line:
            changes += 1
            continue
        deduplicated_lines.append(line)
        prev_line = line
    fixed_text = '\n'.join(deduplicated_lines)
    
    return fixed_text, changes

def try_decode_with_fallback(file_path):
    """Farklı encoding'lerle dosyayı okumayı dene"""
    encodings = ['utf-8', 'latin1', 'cp1254', 'iso-8859-9', 'windows-1254']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
            return text, encoding, True
        except:
            continue
    
    # Hiçbiri işe yaramazsa, hataları yoksay
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        return text, 'utf-8-ignore', False
    except:
        return None, None, False

def fix_mojibake_in_file(file_path, dry_run=False, verbose=True):
    """Bir dosyadaki Mojibake sorunlarını düzelt"""
    try:
        # Dosyayı oku
        text, used_encoding, success = try_decode_with_fallback(file_path)
        
        if text is None:
            if verbose:
                print(f"✗ Okunamadı: {file_path}")
            return False
        
        # Mojibake desenlerini düzelt
        fixed_text, change_count = fix_mojibake_patterns(text)
        
        # Değişiklik olup olmadığını kontrol et
        if change_count > 0:
            # BOM kontrolü
            has_bom = '\ufeff' in text or text.startswith('\ufeff')
            
            if not dry_run:
                # UTF-8 BOM'suz olarak kaydet (backup yok)
                with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(fixed_text)
                
                if verbose:
                    print(f"✓ Düzeltildi: {file_path}")
                    print(f"  {change_count} sorun düzeltildi, encoding: {used_encoding}")
                    if has_bom:
                        print(f"  BOM karakteri temizlendi")
            else:
                if verbose:
                    print(f"! Sorun bulundu: {file_path}")
                    print(f"  {change_count} desen tespit edildi, encoding: {used_encoding}")
                    if has_bom:
                        print(f"  BOM karakteri tespit edildi")
            return True
        else:
            if verbose:
                print(f"○ Temiz: {file_path}")
            return False
            
    except Exception as e:
        if verbose:
            print(f"✗ Hata {file_path}: {e}")
        return False

def remove_backup_files(root_dir, recursive=True):
    """Dizindeki .bak dosyalarını sil"""
    root_path = Path(root_dir).resolve()
    
    if not root_path.exists():
        print(f"Hata: '{root_dir}' dizini bulunamadı!")
        return 0
    
    # .bak dosyalarını bul
    if recursive:
        bak_files = list(root_path.rglob('*.bak'))
    else:
        bak_files = list(root_path.glob('*.bak'))
    
    if not bak_files:
        print(f"'{root_dir}' dizininde .bak dosyası bulunamadı.")
        return 0
    
    print(f"\n{'='*70}")
    print(f"Toplam {len(bak_files)} adet .bak dosyası bulundu.")
    print(f"{'='*70}\n")
    
    deleted_count = 0
    for bak_file in bak_files:
        try:
            bak_file.unlink()
            print(f"✓ Silindi: {bak_file}")
            deleted_count += 1
        except Exception as e:
            print(f"✗ Silinemedi {bak_file}: {e}")
    
    print(f"\n{'='*70}")
    print(f"Silinen .bak dosyası: {deleted_count}/{len(bak_files)}")
    print(f"{'='*70}\n")
    
    return deleted_count

def scan_and_fix_directory(root_dir, dry_run=False, recursive=True, clean_backups=True):
    """Dizini tara ve .py dosyalarını düzelt"""
    root_path = Path(root_dir).resolve()
    
    if not root_path.exists():
        print(f"Hata: '{root_dir}' dizini bulunamadı!")
        return
    
    # Önce .bak dosyalarını temizle
    if clean_backups and not dry_run:
        print(f"\n🗑️  Önceki .bak dosyaları temizleniyor...\n")
        remove_backup_files(root_dir, recursive)
    
    # .py dosyalarını bul
    if recursive:
        py_files = list(root_path.rglob('*.py'))
    else:
        py_files = list(root_path.glob('*.py'))
    
    if not py_files:
        print(f"'{root_dir}' dizininde .py dosyası bulunamadı.")
        return
    
    print(f"\n{'='*70}")
    print(f"Mojibake Düzeltici")
    print(f"{'='*70}")
    print(f"Dizin: {root_path}")
    print(f"Toplam: {len(py_files)} adet .py dosyası")
    print(f"Mod: {'DRY RUN (sadece kontrol)' if dry_run else 'FIX (düzelt)'}")
    print(f"{'='*70}\n")
    
    fixed_count = 0
    for py_file in py_files:
        if fix_mojibake_in_file(py_file, dry_run, verbose=True):
            fixed_count += 1
    
    print(f"\n{'='*70}")
    print(f"İşlem Tamamlandı!")
    print(f"Mojibake {'bulunan' if dry_run else 'düzeltilen'} dosya: {fixed_count}/{len(py_files)}")
    print(f"{'='*70}\n")
    
    return fixed_count

def main():
    """Ana fonksiyon"""
    import sys
    
    print("\n" + "="*70)
    print("Python Mojibake Düzeltici")
    print("Karakter kodlama bozukluklarını tespit eder ve düzeltir")
    print("="*70 + "\n")
    
    # Komut satırı kullanımı
    if len(sys.argv) > 1:
        directory = sys.argv[1]
        dry_run = '--fix' not in sys.argv
        recursive = '--no-recursive' not in sys.argv
        clean_backups = '--keep-backups' not in sys.argv
        
        if '--help' in sys.argv or '-h' in sys.argv:
            print("Kullanım:")
            print(f"  python {sys.argv[0]} [dizin] [--fix] [--no-recursive] [--keep-backups]")
            print("\nSeçenekler:")
            print("  dizin            : Taranacak dizin (varsayılan: mevcut dizin)")
            print("  --fix            : Sadece kontrol yerine düzelt")
            print("  --no-recursive   : Alt dizinleri tarama")
            print("  --keep-backups   : Varolan .bak dosyalarını silme")
            print("\nÖrnekler:")
            print(f"  python {sys.argv[0]} .                    # Mevcut dizini kontrol et")
            print(f"  python {sys.argv[0]} . --fix              # Mevcut dizini düzelt")
            print(f"  python {sys.argv[0]} /path/to/dir --fix   # Belirtilen dizini düzelt")
            print(f"\nNot: Script artık .bak yedekleri oluşturmaz ve varolan .bak'ları siler.")
            return
    else:
        # İnteraktif mod
        directory = input("Taranacak dizin yolu (Enter = mevcut dizin): ").strip()
        if not directory:
            directory = "."
        
        choice = input("\nMod seçin:\n  1) Sadece kontrol et (önerilir)\n  2) Düzelt ve kaydet\nSeçim (1/2): ").strip()
        dry_run = choice != '2'
        
        rec_choice = input("\nAlt dizinleri de tara? (E/h): ").strip().lower()
        recursive = rec_choice != 'h'
        
        clean_backups = True
        if not dry_run:
            bak_choice = input("\nVarolan .bak dosyalarını sil? (E/h): ").strip().lower()
            clean_backups = bak_choice != 'h'
    
    scan_and_fix_directory(directory, dry_run, recursive, clean_backups)

if __name__ == "__main__":
    main()