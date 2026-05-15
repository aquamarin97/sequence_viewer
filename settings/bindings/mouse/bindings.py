from __future__ import annotations

from settings.bindings.mouse.types import MouseButton, MouseContext

BUTTON = "button"
MODIFIER = "modifier"


BUILT_IN_BINDINGS: dict[tuple[str, str], dict[str, str]] = {
    (MouseContext.SEQUENCE_VIEW.value, "drag_select"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.SEQUENCE_VIEW.value, "drag_select_additive"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "Ctrl"},
    (MouseContext.SEQUENCE_VIEW.value, "guide_set"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.SEQUENCE_VIEW.value, "guide_toggle"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "Ctrl"},
    (MouseContext.SEQUENCE_VIEW.value, "zoom"): {BUTTON: MouseButton.WHEEL.value, MODIFIER: "Ctrl"},
    (MouseContext.SEQUENCE_VIEW.value, "h_scroll"): {BUTTON: MouseButton.WHEEL.value, MODIFIER: "Shift"},
    (MouseContext.HEADER_VIEW.value, "row_select"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.HEADER_VIEW.value, "row_multi_select"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "Ctrl"},
    (MouseContext.HEADER_VIEW.value, "row_range_select"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "Shift"},
    (MouseContext.HEADER_VIEW.value, "row_reorder"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.NAVIGATION_RULER.value, "zoom_to_range"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.NAVIGATION_RULER.value, "scroll_to"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.ANNOTATION_VIEW.value, "select"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.ANNOTATION_VIEW.value, "multi_select"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "Ctrl"},
    (MouseContext.ANNOTATION_VIEW.value, "edit"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.CONSENSUS_SPACER.value, "select_all"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.CONSENSUS_SPACER.value, "select_all_additive"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "Ctrl"},
    (MouseContext.CONSENSUS_SPACER.value, "edit_label"): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
}
