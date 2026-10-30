"""AppViewModel tests against seeded mock DB."""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta

import pytest
import time_machine
from app.domain.models import (
    LIST_ALL_ID,
    LIST_FAVORITES_ID,
    LIST_IN_WORK_ID,
    LIST_TODAY_ID,
    TaskKind,
    TimerMode,
)
from app.services.task_service import TaskService
from app.storage.task_repo import TaskRepo
from app.ui.viewmodels.app_view_model import AppViewModel
from app.ui.viewmodels.task_model import TaskModel
from PySide6.QtCore import QCoreApplication

from tests.support.db import SeedResult, seed_demo

T0 = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def qapp() -> QCoreApplication:
    existing = QCoreApplication.instance()
    if existing is not None:
        return existing
    return QCoreApplication([])


@pytest.fixture
def seeded(qapp: QCoreApplication) -> tuple[SeedResult, AppViewModel]:
    with time_machine.travel(T0, tick=False):
        seed = seed_demo(now=T0)
        return seed, AppViewModel(seed.conn)


def _titles(model: TaskModel) -> list[str]:
    return [str(model.data(model.index(i, 0), model.TitleRole)) for i in range(model.rowCount())]


def _task_id_by_title(vm: AppViewModel, title: str) -> int:
    tasks = vm.tasks_model()
    for i in range(tasks.rowCount()):
        if tasks.data(tasks.index(i, 0), tasks.TitleRole) == title:
            return int(tasks.data(tasks.index(i, 0), tasks.IdRole))
    raise AssertionError(f"task {title!r} not found")


def test_defaults_to_all(seeded: tuple[SeedResult, AppViewModel]) -> None:
    _, vm = seeded
    with time_machine.travel(T0, tick=False):
        assert vm.selectedListId == LIST_ALL_ID
        assert vm.lists_model().rowCount() == 5
        assert vm.tasks_model().rowCount() == 3
        vm.openCreateDialog()
        assert vm.createListId == LIST_FAVORITES_ID
        vm.closeCreateDialog()


def test_create_with_parent_and_start_dialog(seeded: tuple[SeedResult, AppViewModel]) -> None:
    seed, vm = seeded
    with time_machine.travel(T0, tick=False) as clock:
        parent_id = _task_id_by_title(vm, "Код")
        vm.openCreateDialog()
        vm.setCreateTitle("Грамматика")
        vm.setCreateDescription("под English")
        vm.setCreateMode(TimerMode.STOPWATCH.value)
        vm.setDraftParentId(parent_id)
        vm.submitCreateDialog()
        assert "Грамматика" in _titles(vm.tasks_model())
        child_id = _task_id_by_title(vm, "Грамматика")
        assert TaskRepo(seed.conn).parent_of(child_id) == parent_id

        vm.startTask(child_id)
        assert vm.startDialogOpen
        vm.setStartNote("учить Present Perfect")
        vm.confirmStart()
        assert not vm.startDialogOpen
        assert vm.engine.open_session_for(child_id) is not None

        clock.shift(timedelta(seconds=5))
        session = vm.engine.open_session_for(child_id)
        assert session is not None
        assert session.note == "учить Present Perfect"

        vm.pauseTask(child_id)
        vm.stopTask(child_id)


def test_create_and_toggle_checklist(seeded: tuple[SeedResult, AppViewModel]) -> None:
    seed, vm = seeded
    with time_machine.travel(T0, tick=False):
        vm.openCreateDialog()
        vm.setCreateTitle("Оплатить счёт")
        vm.setCreateKind(TaskKind.CHECKLIST.value)
        vm.submitCreateDialog()
        task = next(t for t in TaskRepo(seed.conn).list_all() if t.title == "Оплатить счёт")
        assert task.kind is TaskKind.CHECKLIST
        assert vm.engine.open_session_for(task.id) is None

        vm.toggleChecklist(task.id)
        completed = TaskRepo(seed.conn).get(task.id)
        assert completed is not None and completed.is_completed
        vm.toggleChecklist(task.id)
        uncompleted = TaskRepo(seed.conn).get(task.id)
        assert uncompleted is not None and not uncompleted.is_completed


def test_create_task_can_be_in_group_and_favorites(
    seeded: tuple[SeedResult, AppViewModel],
) -> None:
    seed, vm = seeded
    with time_machine.travel(T0, tick=False):
        from app.storage.list_repo import ListRepo

        english = ListRepo(seed.conn).create("English")
        vm.openCreateDialog()
        vm.setCreateListId(english.id)
        vm.setCreateFavorite(True)
        vm.setCreateTitle("Grammar")
        vm.submitCreateDialog()

        task = next(t for t in TaskRepo(seed.conn).list_all() if t.title == "Grammar")
        assert task.list_id == english.id
        assert task.is_favorite

        vm.selectList(LIST_FAVORITES_ID)
        assert "Grammar" in _titles(vm.tasks_model())
        vm.selectList(english.id)
        assert "Grammar" in _titles(vm.tasks_model())


def test_move_task_to_favorites_marks_it_favorite(
    seeded: tuple[SeedResult, AppViewModel],
) -> None:
    seed, vm = seeded
    with time_machine.travel(T0, tick=False):
        from app.storage.list_repo import ListRepo

        english = ListRepo(seed.conn).create("English")
        task = TaskRepo(seed.conn).create(english.id, "Grammar")
        vm.openEditDialog(task.id)
        vm.removeEditTaskFromGroup()

        moved = TaskRepo(seed.conn).get(task.id)
        assert moved is not None
        assert moved.list_id == LIST_FAVORITES_ID
        assert moved.is_favorite
        vm.selectList(LIST_FAVORITES_ID)
        assert "Grammar" in _titles(vm.tasks_model())


def test_history_refresh_does_not_reopen_window(
    seeded: tuple[SeedResult, AppViewModel],
) -> None:
    """Refreshing history must not emit the window-open notification."""
    _, vm = seeded
    open_events: list[None] = []
    vm.historyDialogOpenChanged.connect(lambda: open_events.append(None))

    vm.refresh_history()
    assert open_events == []

    vm.openHistory()
    assert len(open_events) == 1
    vm.refresh_history()
    assert len(open_events) == 1

    vm.closeHistory()
    assert len(open_events) == 2


def test_history_sort_uses_selected_column(
    seeded: tuple[SeedResult, AppViewModel],
) -> None:
    seed, vm = seeded
    with time_machine.travel(T0, tick=False):
        vm.engine.start(seed.tasks["coding"].id, now=T0, use_task_default=False)
        vm.engine.stop(seed.tasks["coding"].id, now=T0 + timedelta(seconds=5))
        vm.engine.start(seed.tasks["review"].id, now=T0, use_task_default=False)
        vm.engine.stop(seed.tasks["review"].id, now=T0 + timedelta(seconds=25))

        vm.setHistorySort("duration")
        durations = [item.duration_seconds for item in vm._filtered_history()]
        assert durations == sorted(durations, key=lambda value: value or -1)

        vm.setHistorySort("task")
        model = vm._history_model
        titles = [
            str(model.data(model.index(index, 0), model.TitleRole))
            for index in range(model.rowCount())
        ]
        assert titles == sorted(titles, key=str.casefold)


def test_history_type_filter_and_reset(seeded: tuple[SeedResult, AppViewModel]) -> None:
    seed, vm = seeded
    with time_machine.travel(T0, tick=False):
        checklist = TaskRepo(seed.conn).create(
            LIST_FAVORITES_ID, "Checklist", kind=TaskKind.CHECKLIST
        )
        TaskService(seed.conn).complete_checklist(checklist.id, now=T0)
        vm.setHistoryTypeFilter("checklist")

        rows = vm._filtered_history()
        assert rows and all(vm._history_type_key(row) == "checklist" for row in rows)
        assert "Чек-листы" in vm._history_filter_summary

        vm.clearHistoryFilters()
        assert vm._history_type_filter == ""
        assert vm._history_filter_summary == ""


def test_history_export_uses_selection_or_filtered_rows(
    seeded: tuple[SeedResult, AppViewModel], tmp_path
) -> None:
    seed, vm = seeded
    with time_machine.travel(T0, tick=False):
        vm.engine.start(seed.tasks["coding"].id, now=T0, use_task_default=False)
        vm.engine.stop(seed.tasks["coding"].id, now=T0 + timedelta(seconds=5))
        vm.engine.start(seed.tasks["review"].id, now=T0, use_task_default=False)
        vm.engine.stop(seed.tasks["review"].id, now=T0 + timedelta(seconds=10))

        rows = vm._filtered_history()
        assert len(rows) == 2

        all_path = tmp_path / "all.csv"
        assert vm.exportHistory(str(all_path), []) == str(all_path)
        with all_path.open(encoding="utf-8-sig", newline="") as handle:
            all_rows = list(csv.DictReader(handle))
        assert {int(row["completion_id"]) for row in all_rows} == {row.id for row in rows}

        vm.setHistoryQuery("Код")
        filtered_rows = vm._filtered_history()
        assert len(filtered_rows) == 1
        filtered_path = tmp_path / "filtered.csv"
        assert vm.exportHistory(str(filtered_path), []) == str(filtered_path)
        with filtered_path.open(encoding="utf-8-sig", newline="") as handle:
            filtered_csv_rows = list(csv.DictReader(handle))
        assert [int(row["completion_id"]) for row in filtered_csv_rows] == [filtered_rows[0].id]
        vm.setHistoryQuery("")

        selected = rows[0]
        selected_path = tmp_path / "selected.csv"
        assert vm.exportHistory(str(selected_path), [selected.id]) == str(selected_path)
        with selected_path.open(encoding="utf-8-sig", newline="") as handle:
            selected_rows = list(csv.DictReader(handle))
        assert [int(row["completion_id"]) for row in selected_rows] == [selected.id]


def test_start_prefills_previous_note(seeded: tuple[SeedResult, AppViewModel]) -> None:
    _, vm = seeded
    with time_machine.travel(T0, tick=False):
        coding_id = _task_id_by_title(vm, "Код")
        vm.startTask(coding_id)
        assert vm.startDialogOpen
        assert vm.startNote == "фича X"
        vm.closeStartDialog()


def test_today_list_shows_due_recurrence(seeded: tuple[SeedResult, AppViewModel]) -> None:
    _, vm = seeded
    with time_machine.travel(T0, tick=False):
        vm.selectList(LIST_TODAY_ID)
        assert vm.tasks_model().rowCount() == 0

        vm.openCreateDialog()
        vm.setCreateTitle("Ежедневная")
        vm.setCreateRecurrenceKind("daily")
        vm.submitCreateDialog()
        assert vm.selectedListId == LIST_TODAY_ID
        assert "Ежедневная" in _titles(vm.tasks_model())


def test_in_work_list_shows_roster(seeded: tuple[SeedResult, AppViewModel]) -> None:
    _, vm = seeded
    with time_machine.travel(T0, tick=False):
        coding_id = _task_id_by_title(vm, "Код")
        vm.startTask(coding_id)
        vm.confirmStart()
        vm.showAllInWork()
        assert vm.selectedListId == LIST_IN_WORK_ID
        assert "Код" in _titles(vm.tasks_model())


def test_work_roster_progress_and_resume(seeded: tuple[SeedResult, AppViewModel]) -> None:
    _, vm = seeded
    with time_machine.travel(T0, tick=False):
        coding_id = _task_id_by_title(vm, "Код")
        vm.startTask(coding_id)
        vm.confirmStart()
        roster = vm.work_roster()
        assert len(roster) >= 1
        row = next(r for r in roster if r.task_id == coding_id)
        assert row.state == "running"
        # Seeded coding task uses stopwatch → no progress scale
        assert row.progress is None
        assert row.clock != "пауза"

        vm.pauseTask(coding_id)
        paused = next(r for r in vm.work_roster() if r.task_id == coding_id)
        assert paused.state == "paused"
        from app.i18n import tr

        assert paused.clock == tr("status.paused")

        vm.resumeTask(coding_id)
        resumed = next(r for r in vm.work_roster() if r.task_id == coding_id)
        assert resumed.state == "running"


def test_edit_can_move_task_into_group(seeded: tuple[SeedResult, AppViewModel]) -> None:
    seed, vm = seeded
    with time_machine.travel(T0, tick=False):
        from app.storage.list_repo import ListRepo

        work_list = next(lst for lst in ListRepo(seed.conn).list_all() if lst.name == "Работа")
        coding_id = _task_id_by_title(vm, "Код")
        coding = TaskRepo(seed.conn).get(coding_id)
        assert coding is not None
        assert coding.list_id == LIST_FAVORITES_ID

        vm.openEditDialog(coding_id)
        vm.setEditListId(work_list.id)
        vm.submitEditDialog()
        moved = TaskRepo(seed.conn).get(coding_id)
        assert moved is not None
        assert moved.list_id == work_list.id


def test_seeded_coding_idle_stopwatch_shows_zero(
    seeded: tuple[SeedResult, AppViewModel],
) -> None:
    """Idle stopwatch cards show 0:00 even if sessions exist today in the DB."""
    _, vm = seeded
    with time_machine.travel(T0, tick=False):
        vm.refresh_tasks()
        tasks = vm.tasks_model()
        times: dict[str, str] = {}
        for i in range(tasks.rowCount()):
            title = str(tasks.data(tasks.index(i, 0), tasks.TitleRole))
            time_today = str(tasks.data(tasks.index(i, 0), tasks.TimeTodayRole))
            times[title] = time_today
        assert times.get("Код") == "0:00"


def _clock_for(vm: AppViewModel, title: str) -> str:
    tasks = vm.tasks_model()
    for i in range(tasks.rowCount()):
        if str(tasks.data(tasks.index(i, 0), tasks.TitleRole)) == title:
            return str(tasks.data(tasks.index(i, 0), tasks.TimeTodayRole))
    raise AssertionError(f"task not found: {title}")


def test_countdown_card_shows_remaining_not_elapsed(
    seeded: tuple[SeedResult, AppViewModel],
) -> None:
    """Running timer (countdown) counts down on the card; stop stacks into today."""
    seed, vm = seeded
    from app.domain.models import TimerMode
    from app.storage.task_repo import TaskRepo

    review = seed.tasks["review"]
    with time_machine.travel(T0, tick=False):
        TaskRepo(seed.conn).update(
            review.id,
            default_mode=TimerMode.COUNTDOWN,
            default_target_seconds=25 * 60,
            update_target=True,
        )
        vm.refresh_tasks()
        # Idle countdown shows the configured timer, not 0:00
        assert _clock_for(vm, "Ревью") == "25:00"
        vm.startTask(review.id)
        vm.confirmStart()
        assert _clock_for(vm, "Ревью") == "25:00"

    with time_machine.travel(T0 + timedelta(seconds=90), tick=False):
        vm.tick()
        assert _clock_for(vm, "Ревью") == "23:30"

    with time_machine.travel(T0 + timedelta(seconds=120), tick=False):
        vm.stopTask(review.id)
        # Idle again → back to configured target (session time still in stats/today)
        assert _clock_for(vm, "Ревью") == "25:00"
        assert vm.engine.task_elapsed_today(review.id) == 120
        vm.startTask(review.id)
        vm.confirmStart()
        assert _clock_for(vm, "Ревью") == "25:00"

    with time_machine.travel(T0 + timedelta(seconds=150), tick=False):
        vm.tick()
        assert _clock_for(vm, "Ревью") == "24:30"
        vm.stopTask(review.id)
        assert _clock_for(vm, "Ревью") == "25:00"
        assert vm.engine.task_elapsed_today(review.id) == 150


def test_work_changed_emits_on_state_not_clock(seeded: tuple[SeedResult, AppViewModel]) -> None:
    """workChanged is for roster membership/state; clock ticks update cache silently."""
    seed, vm = seeded
    emissions: list[int] = []
    vm.workChanged.connect(lambda: emissions.append(1))

    review = seed.tasks["review"]
    with time_machine.travel(T0, tick=False):
        before = len(emissions)
        vm.startTask(review.id)
        vm.confirmStart()
        assert len(emissions) > before  # entered «В работе»

    with time_machine.travel(T0 + timedelta(seconds=5), tick=False):
        before = len(emissions)
        vm.tick()  # clock only
        assert len(emissions) == before
        assert vm.work_roster()[0].clock  # cache still refreshed

    with time_machine.travel(T0 + timedelta(seconds=10), tick=False):
        before = len(emissions)
        vm.pauseTask(review.id)
        assert len(emissions) == before + 1  # running → paused
