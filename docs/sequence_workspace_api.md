# Sequence Workspace API

This document is the integration contract for embedding the sequence viewer
inside a larger Qt application.

## Public Entry Point

Host applications should instantiate and talk to:

```python
from sequence_viewer import SequenceWorkspaceWidget

workspace = SequenceWorkspaceWidget(parent=parent_widget)
```

Everything under `sequence_viewer.features`, `sequence_viewer.graphics`, and
`sequence_viewer.workspace.coordinators` is internal implementation detail.
Host code should not connect to those widgets or reach into `workspace._ctx`.

## Stable Input Types

The facade accepts plain `(header, sequence)` tuples and `SequenceRowInput`
objects:

```python
from sequence_viewer import SequenceRowInput

workspace.load_rows([
    SequenceRowInput("seq-1", "ATGC"),
    ("seq-2", "ATGT"),
])
```

For lazy or pre-built records, pass `SequenceRecord` instances:

```python
workspace.append_records(records)
workspace.load_records(records)
```

Use `alignment_metadata=AlignmentMetadata(...)` when the loaded rows are already
aligned. The viewer owns rendering and consensus behavior after that.

## Public Methods

Data loading and row mutation:

- `load_rows(rows, *, alignment_metadata=None)`
- `append_rows(rows)`
- `load_records(records, *, alignment_metadata=None)`
- `append_records(records, *, alignment_metadata=None)`
- `add_sequence(header, sequence)`
- `clear()`
- `move_row(from_index, to_index)`
- `set_header(index, new_header)`
- `set_aligned(metadata)`
- `clear_alignment()`

Annotation and command entry points:

- `add_annotation(row_index, annotation)`
- `remove_annotation(row_index, annotation_id)`
- `clear_annotations()`
- `delete_rows_with_undo(rows)`
- `delete_annotations_with_undo(annotations)`
- `delete_consensus_annotations_with_undo(annotation_ids)`

Read-only queries:

- `row_count()`
- `all_rows()`
- `selected_rows()`
- `selection_snapshot()`

Dialog/action helpers kept for the standalone development app:

- `open_find_motifs_dialog()`
- `open_edit_annotation_dialog(annotation)`
- `open_edit_consensus_annotation_dialog(annotation)`

## Selection Snapshot

`selection_snapshot()` returns a `SelectionSnapshot` dataclass:

```python
snapshot = workspace.selection_snapshot()
snapshot.selected_rows
snapshot.sequence_range
snapshot.selected_annotations
snapshot.consensus_selected
snapshot.consensus_range
snapshot.consensus_annotation_ids
```

`sequence_range` is `(row_start, row_end, col_start, col_end)` with normalized,
inclusive endpoints. `consensus_range` is `(col_start, col_end)` with inclusive
endpoints when a consensus range is active.

## Advanced Escape Hatch

`workspace.model` remains available for compatibility and development tools, but
new host integration should prefer the facade methods above. Direct model access
can bypass workspace-level interaction cleanup, undo state, and future public
signals.

## Internal Signal Boundary

Internal signal-slot wiring lives in `sequence_viewer/workspace/signal_mapping.py`.
That file connects header, sequence, consensus, annotation, and layout widgets
inside the workspace. A host application should not connect directly to:

- `ctx.sequence_viewer`
- `ctx.header_viewer`
- `ctx.consensus_row`
- `ctx.consensus_spacer`
- `ctx.annotation_layer`
- coordinator or controller objects

If the host needs a new event, add a public signal or snapshot method on
`SequenceWorkspaceWidget` and keep the internal wiring private.
