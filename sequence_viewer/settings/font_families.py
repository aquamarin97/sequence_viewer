# settings/font_families.py
"""
GÃ¶mÃ¼lÃ¼ ve sistem monospace font ailesi yÃ¶netimi.

GÃ¶mÃ¼lÃ¼ fontlar assets/fonts/monospace/ klasÃ¶rÃ¼nde bulunur ve tÃ¼m platformlarda
kullanÄ±labilir. Ek olarak, kullanÄ±cÄ±nÄ±n sisteminde yÃ¼klÃ¼ olan belirli monospace
fontlar (Consolas, Lucida Console gibi) da listeye eklenir.

KullanÄ±m:
    from sequence_viewer.settings.font_families import load_embedded_fonts, get_monospace_fonts
    
    # Uygulama baÅŸlangÄ±cÄ±nda
    load_embedded_fonts()
    
    # Font dropdown'Ä± doldururken
    combo.addItems(get_monospace_fonts())
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# GÃ¶mÃ¼lÃ¼ Fontlar (Uygulamayla birlikte daÄŸÄ±tÄ±lan)
# ---------------------------------------------------------------------------

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent

EMBEDDED_MONOSPACE_FONTS: list[tuple[str, Path]] = [
    ("JetBrains Mono", _PACKAGE_ROOT / "assets" / "fonts" / "monospace" / "JetBrainsMono-Regular.ttf"),
    ("Source Code Pro", _PACKAGE_ROOT / "assets" / "fonts" / "monospace" / "SourceCodePro-Regular.ttf"),
    ("Cascadia Code", _PACKAGE_ROOT / "assets" / "fonts" / "monospace" / "CascadiaCode-Regular.ttf"),
    ("IBM Plex Mono", _PACKAGE_ROOT / "assets" / "fonts" / "monospace" / "IBMPlexMono-Regular.ttf"),
    ("Fira Code", _PACKAGE_ROOT / "assets" / "fonts" / "monospace" / "FiraCode-Regular.ttf"),
]

# ---------------------------------------------------------------------------
# Sistem FontlarÄ± (KullanÄ±cÄ±nÄ±n sisteminde varsa dahil edilir)
# ---------------------------------------------------------------------------

SYSTEM_MONOSPACE_FONTS: list[str] = [
    "Consolas",          # Windows Vista+ yerleÅŸik
    "Lucida Console",    # Windows yerleÅŸik
    "Menlo",             # macOS 10.6+ yerleÅŸik
    "Monaco",            # macOS klasik monospace
    "DejaVu Sans Mono",  # Linux varsayÄ±lanÄ±
    "Liberation Mono",   # Linux/LibreOffice
    "Ubuntu Mono",       # Ubuntu varsayÄ±lanÄ±
]


# ---------------------------------------------------------------------------
# Font YÃ¼kleme ve Listeleme FonksiyonlarÄ±
# ---------------------------------------------------------------------------

_fonts_loaded: bool = False


def load_embedded_fonts() -> None:
    """
    GÃ¶mÃ¼lÃ¼ fontlarÄ± QFontDatabase'e kaydeder.
    
    Uygulama baÅŸlangÄ±cÄ±nda (QApplication oluÅŸturulduktan sonra) bir kez
    Ã§aÄŸrÄ±lmalÄ±dÄ±r. Tekrar Ã§aÄŸrÄ±lÄ±rsa sessizce atlanÄ±r.
    
    Ã–rnek:
        from PyQt5.QtWidgets import QApplication
        from sequence_viewer.settings.font_families import load_embedded_fonts
        
        app = QApplication(sys.argv)
        load_embedded_fonts()
    """
    global _fonts_loaded
    
    if _fonts_loaded:
        return
    
    try:
        from PyQt5.QtGui import QFontDatabase
        
        db = QFontDatabase()
        loaded_count = 0
        
        for font_name, font_path in EMBEDDED_MONOSPACE_FONTS:
            if not font_path.exists():
                print(f"Warning: Font file not found: {font_path}")
                continue
            
            font_id = db.addApplicationFont(str(font_path))
            
            if font_id == -1:
                print(f"Warning: Failed to load font: {font_path}")
            else:
                loaded_count += 1
                # Debug: Hangi font family isimleri yÃ¼klendi?
                families = db.applicationFontFamilies(font_id)
                if families:
                    print(f"Loaded font: {families[0]} from {font_path}")
        
        _fonts_loaded = True
        print(f"Successfully loaded {loaded_count}/{len(EMBEDDED_MONOSPACE_FONTS)} embedded fonts")
        
    except Exception as e:
        print(f"Error loading embedded fonts: {e}")


def get_embedded_monospace_fonts() -> list[str]:
    """
    GÃ¶mÃ¼lÃ¼ monospace font isimlerini dÃ¶ndÃ¼rÃ¼r.
    
    Returns:
        Font family isimleri listesi (Ã¶rn: ["JetBrains Mono", "Source Code Pro", ...])
    """
    return [name for name, _ in EMBEDDED_MONOSPACE_FONTS]


def get_available_system_fonts() -> list[str]:
    """
    SYSTEM_MONOSPACE_FONTS listesinden kullanÄ±cÄ±nÄ±n sisteminde yÃ¼klÃ¼
    olanlarÄ± dÃ¶ndÃ¼rÃ¼r.
    
    Returns:
        Sistemde mevcut olan font isimleri listesi
    """
    try:
        from PyQt5.QtGui import QFontDatabase
        
        db = QFontDatabase()
        installed = set(db.families())
        
        # Sistem fontlarÄ±ndan mevcut olanlarÄ± filtrele
        available = [font for font in SYSTEM_MONOSPACE_FONTS if font in installed]
        
        return available
        
    except Exception:
        return []


def get_monospace_fonts() -> list[str]:
    """
    TÃ¼m kullanÄ±labilir monospace fontlarÄ± dÃ¶ndÃ¼rÃ¼r.
    
    Ã–nce gÃ¶mÃ¼lÃ¼ fontlar, sonra sistemde bulunan ek fontlar listelenir.
    Tekrar eden fontlar filtrelenir.
    
    Returns:
        KullanÄ±labilir tÃ¼m monospace font isimleri
        
    Ã–rnek:
        from sequence_viewer.settings.font_families import get_monospace_fonts
        
        combo = QComboBox()
        combo.addItems(get_monospace_fonts())
    """
    fonts = []
    
    # 1. GÃ¶mÃ¼lÃ¼ fontlarÄ± ekle
    embedded = get_embedded_monospace_fonts()
    fonts.extend(embedded)
    
    # 2. Sistem fontlarÄ±nÄ± ekle (tekrar etmeyenleri)
    system = get_available_system_fonts()
    for font in system:
        if font not in fonts:
            fonts.append(font)
    
    return fonts


def is_font_available(font_name: str) -> bool:
    """
    Belirtilen font'un kullanÄ±labilir olup olmadÄ±ÄŸÄ±nÄ± kontrol eder.
    
    Args:
        font_name: Kontrol edilecek font family ismi
        
    Returns:
        Font kullanÄ±labilir ise True, deÄŸilse False
    """
    return font_name in get_monospace_fonts()


def get_default_monospace_font() -> str:
    """
    VarsayÄ±lan monospace fontunu dÃ¶ndÃ¼rÃ¼r.
    
    Returns:
        Ä°lk kullanÄ±labilir gÃ¶mÃ¼lÃ¼ font, yoksa ilk sistem fontu,
        hiÃ§biri yoksa "Courier New" fallback'i
    """
    fonts = get_monospace_fonts()
    
    if fonts:
        return fonts[0]
    
    # Fallback (hiÃ§bir font yÃ¼klenemezse)
    return "Courier New"

