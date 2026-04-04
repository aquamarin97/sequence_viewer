# features/sequence_viewer/sequence_viewer_interaction.py
from __future__ import annotations
from PyQt5.QtCore import Qt


class InteractionMixin:
    """
    Mouse / wheel event delegation for SequenceViewerView.

    All events are forwarded to self._controller when available.
    Also handles the annotation-strip special case in mousePressEvent.

    Depends on the host providing:
        self._controller
        self._row_layout
        self._per_row_annot_h
        self.char_height
        self.scene
        self.mapToScene()
        self.viewport()
    """

    # ------------------------------------------------------------------
    # Wheel
    # ------------------------------------------------------------------

    def wheelEvent(self, event):
        if self._controller:
            handled = getattr(self._controller, "handle_wheel_event", None)
            if callable(handled) and handled(event):
                return
        super().wheelEvent(event)

    # ------------------------------------------------------------------
    # Mouse press
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())

            if self._is_in_annotation_strip(scene_pos):
                if self._annotation_item_hit(scene_pos):
                    super().mousePressEvent(event)
                    return
                # Annotation strip clicked but no annotation item — start selection
                self._delegate_mouse_press_to_controller(event)
                return

            self._delegate_mouse_press_to_controller(event)
            return

        super().mousePressEvent(event)

    # ------------------------------------------------------------------
    # Mouse move / release
    # ------------------------------------------------------------------

    def mouseMoveEvent(self, event):
        if self._controller:
            handled = getattr(self._controller, "handle_mouse_move", None)
            if callable(handled) and handled(event):
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._controller:
            handled = getattr(self._controller, "handle_mouse_release", None)
            if callable(handled) and handled(event):
                return
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_in_annotation_strip(self, scene_pos) -> bool:
        layout = self._row_layout
        if layout is not None and layout.row_count > 0:
            row = layout.row_at_y(scene_pos.y())
            return layout.is_in_annot_strip(scene_pos.y(), row)
        if self._per_row_annot_h > 0:
            stride = self._per_row_annot_h + self.char_height
            y_in_row = scene_pos.y() % stride if stride > 0 else 0
            return 0 <= y_in_row < self._per_row_annot_h
        return False

    def _annotation_item_hit(self, scene_pos) -> bool:
        from features.annotation_layer.annotation_graphics_item import AnnotationGraphicsItem
        return any(isinstance(it, AnnotationGraphicsItem) for it in self.scene.items(scene_pos))

    def _delegate_mouse_press_to_controller(self, event):
        if self._controller:
            handled = getattr(self._controller, "handle_mouse_press", None)
            if callable(handled) and handled(event):
                return
        super().mousePressEvent(event)
