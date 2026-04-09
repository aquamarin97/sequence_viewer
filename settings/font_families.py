# settings/font_families.py
"""
Gömülü ve sistem monospace font ailesi yönetimi.

Gömülü fontlar assets/fonts/monospace/ klasöründe bulunur ve tüm platformlarda
kullanılabilir. Ek olarak, kullanıcının sisteminde yüklü olan belirli monospace
fontlar (Consolas, Lucida Console gibi) da listeye eklenir.

Kullanım:
    from settings.font_families import load_embedded_fonts, get_monospace_fonts
    
    # Uygulama başlangıcında
    load_embedded_fonts()
    
    # Font dropdown'ı doldururken
    combo.addItems(get_monospace_fonts())
"""
from __future__ import annotations
import os
from typing import Optional

# ---------------------------------------------------------------------------
# Gömülü Fontlar (Uygulamayla birlikte dağıtılan)
# ---------------------------------------------------------------------------

EMBEDDED_MONOSPACE_FONTS: list[tuple[str, str]] = [
    ("JetBrains Mono", "assets/fonts/monospace/JetBrainsMono-Regular.ttf"),
    ("Source Code Pro", "assets/fonts/monospace/SourceCodePro-Regular.ttf"),
    ("Cascadia Code", "assets/fonts/monospace/CascadiaCode-Regular.ttf"),
    ("IBM Plex Mono", "assets/fonts/monospace/IBMPlexMono-Regular.ttf"),
    ("Fira Code", "assets/fonts/monospace/FiraCode-Regular.ttf"),
]

# ---------------------------------------------------------------------------
# Sistem Fontları (Kullanıcının sisteminde varsa dahil edilir)
# ---------------------------------------------------------------------------

SYSTEM_MONOSPACE_FONTS: list[str] = [
    "Consolas",          # Windows Vista+ yerleşik
    "Lucida Console",    # Windows yerleşik
    "Menlo",             # macOS 10.6+ yerleşik
    "Monaco",            # macOS klasik monospace
    "DejaVu Sans Mono",  # Linux varsayılanı
    "Liberation Mono",   # Linux/LibreOffice
    "Ubuntu Mono",       # Ubuntu varsayılanı
]


# ---------------------------------------------------------------------------
# Font Yükleme ve Listeleme Fonksiyonları
# ---------------------------------------------------------------------------

_fonts_loaded: bool = False


def load_embedded_fonts() -> None:
    """
    Gömülü fontları QFontDatabase'e kaydeder.
    
    Uygulama başlangıcında (QApplication oluşturulduktan sonra) bir kez
    çağrılmalıdır. Tekrar çağrılırsa sessizce atlanır.
    
    Örnek:
        from PyQt5.QtWidgets import QApplication
        from settings.font_families import load_embedded_fonts
        
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
            if not os.path.exists(font_path):
                print(f"Warning: Font file not found: {font_path}")
                continue
            
            font_id = db.addApplicationFont(font_path)
            
            if font_id == -1:
                print(f"Warning: Failed to load font: {font_path}")
            else:
                loaded_count += 1
                # Debug: Hangi font family isimleri yüklendi?
                families = db.applicationFontFamilies(font_id)
                if families:
                    print(f"Loaded font: {families[0]} from {font_path}")
        
        _fonts_loaded = True
        print(f"Successfully loaded {loaded_count}/{len(EMBEDDED_MONOSPACE_FONTS)} embedded fonts")
        
    except Exception as e:
        print(f"Error loading embedded fonts: {e}")


def get_embedded_monospace_fonts() -> list[str]:
    """
    Gömülü monospace font isimlerini döndürür.
    
    Returns:
        Font family isimleri listesi (örn: ["JetBrains Mono", "Source Code Pro", ...])
    """
    return [name for name, _ in EMBEDDED_MONOSPACE_FONTS]


def get_available_system_fonts() -> list[str]:
    """
    SYSTEM_MONOSPACE_FONTS listesinden kullanıcının sisteminde yüklü
    olanları döndürür.
    
    Returns:
        Sistemde mevcut olan font isimleri listesi
    """
    try:
        from PyQt5.QtGui import QFontDatabase
        
        db = QFontDatabase()
        installed = set(db.families())
        
        # Sistem fontlarından mevcut olanları filtrele
        available = [font for font in SYSTEM_MONOSPACE_FONTS if font in installed]
        
        return available
        
    except Exception:
        return []


def get_monospace_fonts() -> list[str]:
    """
    Tüm kullanılabilir monospace fontları döndürür.
    
    Önce gömülü fontlar, sonra sistemde bulunan ek fontlar listelenir.
    Tekrar eden fontlar filtrelenir.
    
    Returns:
        Kullanılabilir tüm monospace font isimleri
        
    Örnek:
        from settings.font_families import get_monospace_fonts
        
        combo = QComboBox()
        combo.addItems(get_monospace_fonts())
    """
    fonts = []
    
    # 1. Gömülü fontları ekle
    embedded = get_embedded_monospace_fonts()
    fonts.extend(embedded)
    
    # 2. Sistem fontlarını ekle (tekrar etmeyenleri)
    system = get_available_system_fonts()
    for font in system:
        if font not in fonts:
            fonts.append(font)
    
    return fonts


def is_font_available(font_name: str) -> bool:
    """
    Belirtilen font'un kullanılabilir olup olmadığını kontrol eder.
    
    Args:
        font_name: Kontrol edilecek font family ismi
        
    Returns:
        Font kullanılabilir ise True, değilse False
    """
    return font_name in get_monospace_fonts()


def get_default_monospace_font() -> str:
    """
    Varsayılan monospace fontunu döndürür.
    
    Returns:
        İlk kullanılabilir gömülü font, yoksa ilk sistem fontu,
        hiçbiri yoksa "Courier New" fallback'i
    """
    fonts = get_monospace_fonts()
    
    if fonts:
        return fonts[0]
    
    # Fallback (hiçbir font yüklenemezse)
    return "Courier New"