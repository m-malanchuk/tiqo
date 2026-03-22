"""Task delete modes."""

from __future__ import annotations

from app.domain.models import LIST_FAVORITES_ID, EndReason
from app.domain.timeutil import utc_now
from app.services.task_service import TaskService
from app.storage.session_repo import SessionRepo
from app.storage.task_repo import TaskRepo

from tests.support.db import make_db


def test_delete_this_only_detaches_children() -> None:
    conn = make_db()
    tasks = TaskRepo(conn)
    sessions = SessionRepo(conn)
    svc = TaskService(conn)

    parent = tasks.create(LIST_FAVORITES_ID, "Parent")
    child = tasks.create(LIST_FAVORITES_ID, "Child")
    svc.set_parent(child.id, parent.id)
    started = utc_now()
    row = sessions.create(parent.id, started_at=started, note="x")
    sessions.close(row.id, ended_at=started, end_reason=EndReason.STOPPED)

    deleted = svc.delete_task(parent.id, mode="this_only")
    assert deleted == [parent.id]
    assert tasks.get(parent.id) is None
    child_after = tasks.get(child.id)
    assert child_after is not None
    assert child_after.parent_task_id is None
    assert sessions.count_for_task(parent.id) == 0


def test_delete_cascade_removes_descendants() -> None:
    conn = make_db()
    tasks = TaskRepo(conn)
    svc = TaskService(conn)

    parent = tasks.create(LIST_FAVORITES_ID, "Parent")
    child = tasks.create(LIST_FAVORITES_ID, "Child")
    grand = tasks.create(LIST_FAVORITES_ID, "Grand")
    svc.set_parent(child.id, parent.id)
    svc.set_parent(grand.id, child.id)

    deleted = svc.delete_task(parent.id, mode="cascade")
    assert set(deleted) == {parent.id, child.id, grand.id}
    assert tasks.get(parent.id) is None
    assert tasks.get(child.id) is None
    assert tasks.get(grand.id) is None
