"""Build a display forest for task nesting (single-parent tree)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.domain.models import Task


@dataclass(frozen=True, slots=True)
class TreeRow:
    task: Task
    depth: int
    is_last_sibling: bool
    # Columns 0..depth-2: full-height vertical where an ancestor still has siblings below.
    ancestor_continues: tuple[bool, ...]
    has_children: bool


def build_task_forest(
    *,
    seed_tasks: list[Task],
    all_tasks: dict[int, Task],
    children_of: dict[int, list[int]],
    parents_of: dict[int, list[int]],
) -> list[TreeRow]:
    """Return tree rows for UI."""
    visible: set[int] = {t.id for t in seed_tasks}
    stack = list(visible)
    while stack:
        current = stack.pop()
        for child_id in children_of.get(current, []):
            if child_id not in visible and child_id in all_tasks:
                visible.add(child_id)
                stack.append(child_id)

    seed_ids = {t.id for t in seed_tasks}
    roots: list[int] = []
    for task_id in sorted(visible, key=lambda i: (all_tasks[i].title.lower(), i)):
        parents_in_view = [p for p in parents_of.get(task_id, []) if p in visible]
        if parents_in_view:
            continue
        if task_id in seed_ids or not parents_of.get(task_id, []):
            roots.append(task_id)

    rows: list[TreeRow] = []

    def walk(
        task_id: int,
        depth: int,
        ancestors: set[int],
        is_last: bool,
        continues: tuple[bool, ...],
    ) -> None:
        if task_id not in visible or task_id in ancestors:
            return
        kids = [c for c in children_of.get(task_id, []) if c in visible]
        rows.append(
            TreeRow(
                task=all_tasks[task_id],
                depth=depth,
                is_last_sibling=is_last,
                ancestor_continues=continues,
                has_children=bool(kids),
            )
        )
        next_ancestors = ancestors | {task_id}
        for index, child_id in enumerate(kids):
            child_last = index == len(kids) - 1
            # Root rows don't push a continue flag (root-among-roots ≠ tree branch).
            # Deeper nodes push whether THIS node still has siblings after it.
            child_continues = continues if depth == 0 else continues + (not is_last,)
            walk(child_id, depth + 1, next_ancestors, child_last, child_continues)

    for index, root_id in enumerate(roots):
        walk(root_id, 0, set(), index == len(roots) - 1, ())

    return rows


def filter_collapsed(rows: list[TreeRow], collapsed_ids: set[int]) -> list[TreeRow]:
    """Hide descendants of collapsed parents (parents themselves stay visible)."""
    if not collapsed_ids:
        return rows
    out: list[TreeRow] = []
    skip_deeper_than: int | None = None
    for node in rows:
        if skip_deeper_than is not None:
            if node.depth > skip_deeper_than:
                continue
            skip_deeper_than = None
        out.append(node)
        if node.task.id in collapsed_ids and node.has_children:
            skip_deeper_than = node.depth
    return out


def index_links(
    parent_child_pairs: list[tuple[int, int]],
) -> tuple[dict[int, list[int]], dict[int, list[int]]]:
    children: dict[int, list[int]] = defaultdict(list)
    parents: dict[int, list[int]] = defaultdict(list)
    for parent_id, child_id in parent_child_pairs:
        children[parent_id].append(child_id)
        parents[child_id].append(parent_id)
    for key in children:
        children[key] = sorted(set(children[key]))
    for key in parents:
        parents[key] = sorted(set(parents[key]))
    return dict(children), dict(parents)
