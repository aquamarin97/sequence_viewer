# settings/scrollbar_style.py
from __future__ import annotations
from PyQt5.QtWidgets import QWidget
from sequence_viewer.settings.theme import AppTheme, theme_manager

def _build_qss(t):
    if t.name == "dark":
        track=_hex(t.row_bg_even.darker(130)); handle=_hex(t.border_drag)
        handle_hover=_hex(t.drop_indicator); handle_press=_hex(t.row_bg_selected_hover)
        arrow_bg=_hex(t.row_bg_odd); arrow_fg=_hex(t.text_primary); border_color=_hex(t.border_normal)
    else:
        track=_hex(t.row_bg_odd.darker(105)); handle=_hex(t.border_normal.darker(130))
        handle_hover=_hex(t.border_drag); handle_press=_hex(t.drop_indicator)
        arrow_bg=_hex(t.row_bg_even); arrow_fg=_hex(t.text_primary); border_color=_hex(t.border_normal)
    return f"""
QScrollBar:vertical {{background:{track};width:12px;margin:12px 0;border:1px solid {border_color};border-radius:2px;}}
QScrollBar::handle:vertical {{background:{handle};min-height:24px;border-radius:2px;margin:1px 2px;}}
QScrollBar::handle:vertical:hover {{background:{handle_hover};}}
QScrollBar::handle:vertical:pressed {{background:{handle_press};}}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{background:{arrow_bg};height:12px;subcontrol-origin:margin;border:1px solid {border_color};}}
QScrollBar::sub-line:vertical {{subcontrol-position:top;}}
QScrollBar::add-line:vertical {{subcontrol-position:bottom;}}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {{background:none;}}
QScrollBar:horizontal {{background:{track};height:12px;margin:0 12px;border:1px solid {border_color};border-radius:2px;}}
QScrollBar::handle:horizontal {{background:{handle};min-width:24px;border-radius:2px;margin:2px 1px;}}
QScrollBar::handle:horizontal:hover {{background:{handle_hover};}}
QScrollBar::handle:horizontal:pressed {{background:{handle_press};}}
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal {{background:{arrow_bg};width:12px;subcontrol-origin:margin;border:1px solid {border_color};}}
QScrollBar::sub-line:horizontal {{subcontrol-position:left;}}
QScrollBar::add-line:horizontal {{subcontrol-position:right;}}
QScrollBar::add-page:horizontal,QScrollBar::sub-page:horizontal {{background:none;}}
"""

def _hex(color): return color.name()

def apply_scrollbar_style(widget):
    widget.setStyleSheet(_build_qss(theme_manager.current))


