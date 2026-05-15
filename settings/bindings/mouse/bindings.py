from __future__ import annotations

from settings.bindings.mouse.types import (
    AnnotationActions,
    ConsensusSpacerActions,
    HeaderActions,
    MouseButton,
    MouseContext,
    NavigationRulerActions,
    SequenceActions,
)

BUTTON = "button"
MODIFIER = "modifier"


BUILT_IN_BINDINGS: dict[tuple[str, str], dict[str, str]] = {
    (MouseContext.SEQUENCE_VIEW.value, SequenceActions.DRAG_SELECT): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.SEQUENCE_VIEW.value, SequenceActions.DRAG_SELECT_ADDITIVE): {BUTTON: MouseButton.LEFT.value, MODIFIER: "Ctrl"},
    (MouseContext.SEQUENCE_VIEW.value, SequenceActions.GUIDE_SET): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.SEQUENCE_VIEW.value, SequenceActions.GUIDE_TOGGLE): {BUTTON: MouseButton.LEFT.value, MODIFIER: "Ctrl"},
    (MouseContext.SEQUENCE_VIEW.value, SequenceActions.ZOOM): {BUTTON: MouseButton.WHEEL.value, MODIFIER: "Ctrl"},
    (MouseContext.SEQUENCE_VIEW.value, SequenceActions.H_SCROLL): {BUTTON: MouseButton.WHEEL.value, MODIFIER: "Shift"},
    (MouseContext.HEADER_VIEW.value, HeaderActions.ROW_SELECT): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.HEADER_VIEW.value, HeaderActions.ROW_MULTI_SELECT): {BUTTON: MouseButton.LEFT.value, MODIFIER: "Ctrl"},
    (MouseContext.HEADER_VIEW.value, HeaderActions.ROW_RANGE_SELECT): {BUTTON: MouseButton.LEFT.value, MODIFIER: "Shift"},
    (MouseContext.HEADER_VIEW.value, HeaderActions.ROW_REORDER): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.NAVIGATION_RULER.value, NavigationRulerActions.ZOOM_TO_RANGE): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.NAVIGATION_RULER.value, NavigationRulerActions.SCROLL_TO): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.ANNOTATION_VIEW.value, AnnotationActions.SELECT): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.ANNOTATION_VIEW.value, AnnotationActions.MULTI_SELECT): {BUTTON: MouseButton.LEFT.value, MODIFIER: "Ctrl"},
    (MouseContext.ANNOTATION_VIEW.value, AnnotationActions.EDIT): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.CONSENSUS_SPACER.value, ConsensusSpacerActions.SELECT_ALL): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
    (MouseContext.CONSENSUS_SPACER.value, ConsensusSpacerActions.SELECT_ALL_ADDITIVE): {BUTTON: MouseButton.LEFT.value, MODIFIER: "Ctrl"},
    (MouseContext.CONSENSUS_SPACER.value, ConsensusSpacerActions.EDIT_LABEL): {BUTTON: MouseButton.LEFT.value, MODIFIER: "None"},
}
