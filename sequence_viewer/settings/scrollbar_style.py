# ui/styles/scrollbar.py
"""
Application-wide scrollbar stylesheet builder.

Integrates with ``AppTheme`` / ``ThemeManager`` to produce theme-aware QSS
and optionally keeps any registered widget in sync when the active theme
changes at runtime.

Usage (one-shot)::

    from ui.styles.scrollbar import ScrollbarStyle
    ScrollbarStyle.apply(my_widget)

Usage (live theme tracking)::

    from ui.styles.scrollbar import ScrollbarStyle
    ScrollbarStyle.attach(my_widget)   # re-applies automatically on theme change
    # later, if the widget is destroyed early:
    ScrollbarStyle.detach(my_widget)
"""

from __future__ import annotations

import weakref
from typing import TYPE_CHECKING

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget

# ---------------------------------------------------------------------------
# Theme import — adjust the import path to match your actual package layout.
# ---------------------------------------------------------------------------
from sequence_viewer.settings.theme import AppTheme, theme_manager

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_hex(color: QColor) -> str:
    """Return the ``#rrggbb`` representation of *color*."""
    return color.name()


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------

class _ScrollbarTokens:
    """
    Holds the six colour tokens required to render the scrollbar.

    Keeping token resolution in one place makes it trivial to support
    additional themes in the future without touching the QSS template.
    """

    __slots__ = (
        "track",
        "handle",
        "handle_hover",
        "handle_press",
        "border",
    )

    def __init__(
        self,
        track: str,
        handle: str,
        handle_hover: str,
        handle_press: str,
        border: str,
    ) -> None:
        self.track = track
        self.handle = handle
        self.handle_hover = handle_hover
        self.handle_press = handle_press
        self.border = border

    @classmethod
    def from_theme(cls, theme: AppTheme) -> "_ScrollbarTokens":
        """Derive scrollbar colour tokens from *theme*."""
        if theme.name == "dark":
            return cls(
                track=_to_hex(theme.row_bg_even.darker(130)),
                handle=_to_hex(theme.border_drag),
                handle_hover=_to_hex(theme.drop_indicator),
                handle_press=_to_hex(theme.row_bg_selected_hover),
                border=_to_hex(theme.border_normal),
            )
        # light (default)
        return cls(
            track=_to_hex(theme.row_bg_odd.darker(105)),
            handle=_to_hex(theme.border_normal.darker(130)),
            handle_hover=_to_hex(theme.border_drag),
            handle_press=_to_hex(theme.drop_indicator),
            border=_to_hex(theme.border_normal),
        )


# ---------------------------------------------------------------------------
# QSS template
# ---------------------------------------------------------------------------

_SCROLLBAR_SIZE = 12          # px — total width/height of the scrollbar track
_HANDLE_MIN = 24              # px — minimum draggable handle length
_HANDLE_RADIUS = 3            # px — border-radius on the handle
_TRACK_RADIUS = 3             # px — border-radius on the track


def _build_qss(tokens: _ScrollbarTokens) -> str:
    """Return the complete QSS string for both scroll-bar orientations."""
    t = tokens  # short alias for readability inside the f-string

    return f"""
/* ── Vertical scrollbar ─────────────────────────────────────────────── */
QScrollBar:vertical {{
    background:     {t.track};
    width:          {_SCROLLBAR_SIZE}px;
    margin:         0;
    border:         1px solid {t.border};
    border-radius:  {_TRACK_RADIUS}px;
}}

QScrollBar::handle:vertical {{
    background:     {t.handle};
    min-height:     {_HANDLE_MIN}px;
    border-radius:  {_HANDLE_RADIUS}px;
    margin:         1px 2px;
}}
QScrollBar::handle:vertical:hover   {{ background: {t.handle_hover};  }}
QScrollBar::handle:vertical:pressed {{ background: {t.handle_press}; }}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; border: none; background: none; }}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{ background: none; }}


/* ── Horizontal scrollbar ───────────────────────────────────────────── */
QScrollBar:horizontal {{
    background:     {t.track};
    height:         {_SCROLLBAR_SIZE}px;
    margin:         0;
    border:         1px solid {t.border};
    border-radius:  {_TRACK_RADIUS}px;
}}

QScrollBar::handle:horizontal {{
    background:     {t.handle};
    min-width:      {_HANDLE_MIN}px;
    border-radius:  {_HANDLE_RADIUS}px;
    margin:         2px 1px;
}}
QScrollBar::handle:horizontal:hover   {{ background: {t.handle_hover};  }}
QScrollBar::handle:horizontal:pressed {{ background: {t.handle_press}; }}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{ width: 0; border: none; background: none; }}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{ background: none; }}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class _ThemeChangeRelay(QObject):
    """
    Internal QObject that listens to ``ThemeManager.theme_changed`` and
    re-applies the scrollbar stylesheet to every tracked widget.

    Uses ``weakref.WeakSet`` so that destroyed widgets are released
    automatically without an explicit :py:meth:`detach` call.
    """

    def __init__(self) -> None:
        super().__init__()
        self._tracked: weakref.WeakSet[QWidget] = weakref.WeakSet()
        theme_manager.themeChanged.connect(self._on_theme_changed)

    def track(self, widget: QWidget) -> None:
        self._tracked.add(widget)

    def untrack(self, widget: QWidget) -> None:
        self._tracked.discard(widget)

    @pyqtSlot()
    def _on_theme_changed(self) -> None:
        qss = ScrollbarStyle.build_qss()
        for widget in list(self._tracked):
            widget.setStyleSheet(qss)


# Module-level singleton — created lazily on first use.
_relay: _ThemeChangeRelay | None = None


def _get_relay() -> _ThemeChangeRelay:
    global _relay
    if _relay is None:
        _relay = _ThemeChangeRelay()
    return _relay


class ScrollbarStyle:
    """
    Stateless façade for scrollbar stylesheet operations.

    All methods are class-methods; no instantiation required.
    """

    # ------------------------------------------------------------------
    # Core builders
    # ------------------------------------------------------------------

    @classmethod
    def build_qss(cls, theme: AppTheme | None = None) -> str:
        """
        Return the QSS string for *theme* (defaults to the active theme).

        Parameters
        ----------
        theme:
            An explicit :class:`AppTheme` instance to use.  When *None* the
            currently active theme from ``theme_manager`` is used.
        """
        resolved_theme = theme if theme is not None else theme_manager.current
        tokens = _ScrollbarTokens.from_theme(resolved_theme)
        return _build_qss(tokens)

    # ------------------------------------------------------------------
    # One-shot application
    # ------------------------------------------------------------------

    @classmethod
    def apply(cls, widget: QWidget, theme: AppTheme | None = None) -> None:
        """
        Apply the scrollbar stylesheet to *widget* once.

        The stylesheet is **not** updated automatically if the theme changes
        later.  Use :py:meth:`attach` for live tracking.

        Parameters
        ----------
        widget:
            The target widget.  Its existing stylesheet is replaced entirely.
        theme:
            Optional explicit theme; falls back to the active theme.
        """
        widget.setStyleSheet(cls.build_qss(theme))

    # ------------------------------------------------------------------
    # Live tracking
    # ------------------------------------------------------------------

    @classmethod
    def attach(cls, widget: QWidget) -> None:
        """
        Apply the scrollbar stylesheet to *widget* and keep it in sync
        with future theme changes.

        Parameters
        ----------
        widget:
            The target widget.  Destroyed widgets are released automatically.
        """
        cls.apply(widget)
        _get_relay().track(widget)

    @classmethod
    def detach(cls, widget: QWidget) -> None:
        """
        Stop tracking *widget* for automatic theme updates.

        Safe to call even if *widget* was never :py:meth:`attach`\\ ed.
        """
        if _relay is not None:
            _relay.untrack(widget)