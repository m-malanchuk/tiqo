"""TaskModel must not reset when only live clock fields change (keeps scroll)."""

from __future__ import annotations

from app.ui.viewmodels.task_model import TaskModel, TaskRow


def _row(task_id: int, clock: str, *, running: bool = False) -> TaskRow:
    return TaskRow(
        id=task_id,
        title=f"T{task_id}",
        description="",
        mode="stopwatch",
        time_today=clock,
        work_state="running" if running else "",
        can_start=not running,
        can_pause=running,
        can_stop=running,
        depth=0,
        is_nested=False,
        is_last_sibling=True,
        ancestor_continues=(),
        has_children=False,
        is_expanded=True,
    )


def test_live_clock_update_emits_data_changed_not_reset() -> None:
    model = TaskModel()
    model.reset_items([_row(1, "0:00"), _row(2, "0:00")])

    resets = {"n": 0}
    changes = {"n": 0}

    model.modelAboutToBeReset.connect(lambda: resets.__setitem__("n", resets["n"] + 1))
    model.dataChanged.connect(lambda *_: changes.__setitem__("n", changes["n"] + 1))

    model.reset_items([_row(1, "0:05", running=True), _row(2, "0:00")])
    assert resets["n"] == 0
    assert changes["n"] == 1
    assert model.data(model.index(0, 0), model.TimeTodayRole) == "0:05"


def test_structure_change_still_resets() -> None:
    model = TaskModel()
    model.reset_items([_row(1, "0:00")])
    resets = {"n": 0}
    model.modelAboutToBeReset.connect(lambda: resets.__setitem__("n", resets["n"] + 1))
    model.reset_items([_row(1, "0:00"), _row(2, "0:00")])
    assert resets["n"] == 1
