"""Task forest nesting for UI (single-parent tree)."""

from __future__ import annotations

from app.domain.emoji_catalog import filter_emojis
from app.domain.models import LIST_FAVORITES_ID
from app.services.task_service import TaskService
from app.services.task_tree import build_task_forest, index_links
from app.storage.task_repo import TaskRepo

from tests.support.db import make_db


def test_child_nested_once_under_single_parent() -> None:
    conn = make_db()
    tasks = TaskRepo(conn)
    svc = TaskService(conn)

    parent = tasks.create(LIST_FAVORITES_ID, "A")
    child = tasks.create(LIST_FAVORITES_ID, "Child")
    svc.set_parent(child.id, parent.id)

    all_tasks = {t.id: t for t in tasks.list_all()}
    children, parents = index_links(tasks.parent_child_pairs())
    rows = build_task_forest(
        seed_tasks=list(all_tasks.values()),
        all_tasks=all_tasks,
        children_of=children,
        parents_of=parents,
    )
    child_nodes = [node for node in rows if node.task.id == child.id]
    assert len(child_nodes) == 1
    assert child_nodes[0].depth == 1
    assert child_nodes[0].is_last_sibling is True


def test_third_level_and_ancestor_continues() -> None:
    conn = make_db()
    tasks = TaskRepo(conn)
    svc = TaskService(conn)
    parent = tasks.create(LIST_FAVORITES_ID, "English")
    grammar = tasks.create(LIST_FAVORITES_ID, "Grammar")
    vocab = tasks.create(LIST_FAVORITES_ID, "Vocab")
    nested = tasks.create(LIST_FAVORITES_ID, "Present")
    svc.set_parent(grammar.id, parent.id)
    svc.set_parent(vocab.id, parent.id)
    svc.set_parent(nested.id, grammar.id)

    all_tasks = {t.id: t for t in tasks.list_all()}
    children, parents = index_links(tasks.parent_child_pairs())
    rows = build_task_forest(
        seed_tasks=list(all_tasks.values()),
        all_tasks=all_tasks,
        children_of=children,
        parents_of=parents,
    )
    by_title = {node.task.title: node for node in rows}
    assert by_title["Grammar"].is_last_sibling is False
    assert by_title["Vocab"].is_last_sibling is True
    assert by_title["Present"].depth == 2
    assert by_title["Present"].ancestor_continues == (True,)


def test_emoji_filter_shortcode() -> None:
    found = filter_emojis(":folder:")
    assert any(item.glyph == "📁" for item in found)
    assert filter_emojis("laptop")
