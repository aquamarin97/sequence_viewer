from __future__ import annotations

from typing import Iterable, List, Optional

from sequence_viewer.model.annotation import Annotation


class AnnotationCollection:
    """Reusable annotation CRUD with parent-child removal support."""

    def __init__(
        self,
        label: str,
        *,
        items: Optional[Iterable[Annotation]] = None,
        added_signal=None,
        removed_signal=None,
        updated_signal=None,
    ) -> None:
        self._label = label
        self._items: List[Annotation] = list(items or [])
        self._added_signal = added_signal
        self._removed_signal = removed_signal
        self._updated_signal = updated_signal

    def add(self, annotation: Annotation) -> None:
        if any(item.id == annotation.id for item in self._items):
            raise ValueError(f"{self._label} annotation id '{annotation.id}' already exists.")
        self._items.append(annotation)
        if self._added_signal is not None:
            self._added_signal.emit(annotation)

    def remove(self, annotation_id: str) -> None:
        remove_ids = {annotation_id}
        target = self.find(annotation_id)
        if target is not None and target.parent_id is None:
            remove_ids.update(item.id for item in self._items if item.parent_id == annotation_id)

        kept = [item for item in self._items if item.id not in remove_ids]
        if len(kept) == len(self._items):
            raise KeyError(f"{self._label} annotation '{annotation_id}' not found.")

        self._items[:] = kept
        if self._removed_signal is not None:
            self._removed_signal.emit(annotation_id)

    def update(self, annotation: Annotation) -> None:
        for index, item in enumerate(self._items):
            if item.id == annotation.id:
                self._items[index] = annotation
                if self._updated_signal is not None:
                    self._updated_signal.emit(annotation)
                return
        raise KeyError(f"{self._label} annotation '{annotation.id}' not found.")

    def clear(self) -> None:
        self._items.clear()

    def find(self, annotation_id: str) -> Optional[Annotation]:
        return next((item for item in self._items if item.id == annotation_id), None)

    def all(self) -> List[Annotation]:
        return list(self._items)

    def replace_all(self, annotations: Iterable[Annotation]) -> None:
        self._items = list(annotations)
