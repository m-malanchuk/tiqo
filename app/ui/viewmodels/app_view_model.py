"""AppViewModel — lists, tasks, work roster, create/edit/start dialogs."""

from __future__ import annotations

import contextlib
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.application.models import HistoryRow, WorkRow
from app.application.task_presentation import (
    build_task_rows,
    build_work_rows,
    seed_tasks_for_list,
)
from app.domain.formatting import format_duration
from app.domain.models import (
    LIST_ALL_ID,
    LIST_FAVORITES_ID,
    LIST_IN_WORK_ID,
    LIST_TODAY_ID,
    LISTS_WITHOUT_DESCRIPTION,
    CompletionKind,
    RecurrenceKind,
    TaskCompletion,
    TaskKind,
    TaskList,
    TimerMode,
)
from app.domain.timeutil import local_today
from app.i18n import list_title, tr
from app.services import settings_keys
from app.services.history_export import HistoryExporter
from app.services.notifier import Notifier, NullNotifier
from app.services.task_service import TaskService
from app.services.timer_engine import (
    HierarchyConflictError,
    NoActiveSessionError,
    TimerEngine,
)
from app.storage.assignment_repo import AssignmentRepo
from app.storage.completion_repo import CompletionRepo
from app.storage.list_repo import ListRepo
from app.storage.recurrence_repo import RecurrenceRepo
from app.storage.session_repo import SessionRepo
from app.storage.settings_repo import SettingsRepo
from app.storage.task_repo import TaskRepo
from app.storage.work_repo import WorkRepo
from app.ui.viewmodels.dialogs_mixin import DialogsMixin
from app.ui.viewmodels.emoji_model import EmojiModel
from app.ui.viewmodels.history_model import HistoryModel
from app.ui.viewmodels.list_model import ListModel
from app.ui.viewmodels.picker_model import PickerModel
from app.ui.viewmodels.task_model import TaskModel


class AppViewModel(DialogsMixin, QObject):
    listsChanged = Signal()
    tasksChanged = Signal()
    workChanged = Signal()
    selectionChanged = Signal()
    statusChanged = Signal()
    createDialogChanged = Signal()
    listDialogChanged = Signal()
    editDialogChanged = Signal()
    deleteDialogChanged = Signal()
    startDialogChanged = Signal()
    parentPickerChanged = Signal()
    emojiPickerOpenChanged = Signal()
    emojiQueryChanged = Signal()
    historyDialogChanged = Signal()
    historyDialogOpenChanged = Signal()
    historyNoteDialogChanged = Signal()
    scheduleDialogChanged = Signal()
    sessionNoteDialogChanged = Signal()

    def __init__(
        self,
        conn: sqlite3.Connection,
        parent: QObject | None = None,
        *,
        notifier: Notifier | None = None,
    ) -> None:
        # DialogsMixin has no __init__; bind QObject explicitly (mixin-first MRO).
        QObject.__init__(self, parent)
        self._conn = conn
        self._lists_repo = ListRepo(conn)
        self._tasks_repo = TaskRepo(conn)
        self._sessions_repo = SessionRepo(conn)
        self._work_repo = WorkRepo(conn)
        self._recurrence_repo = RecurrenceRepo(conn)
        self._settings = SettingsRepo(conn)
        self._tasks_svc = TaskService(conn)
        self._assignments = AssignmentRepo(conn)
        self._completions = CompletionRepo(conn)
        self._engine = TimerEngine(conn)
        self._notifier: Notifier = notifier or NullNotifier()

        self._lists_model = ListModel(self)
        self._tasks_model = TaskModel(self)
        self._parent_picker = PickerModel(self)
        self._list_picker = PickerModel(self)
        self._emoji_model = EmojiModel(self)
        self._history_model = HistoryModel(self)
        self._history_open = False
        self._history_query = ""
        self._history_from = ""
        self._history_to = ""
        self._history_type_filter = ""
        self._history_sort_key = "date"
        self._history_sort_ascending = False
        self._history_summary = ""
        self._history_day_summary = ""
        self._history_type_summary = ""
        self._history_filter_summary = ""
        self._history_note_open = False
        self._history_note_completion_id = 0
        self._history_note_task_title = ""
        self._history_note = ""
        self._schedule_open = False
        self._schedule_task_id = 0
        self._schedule_task_title = ""
        self._schedule_date = local_today().isoformat()
        self._session_note_open = False
        self._session_note_task_id = 0
        self._session_note_task_title = ""
        self._session_note = ""

        self._selected_list_id = LIST_ALL_ID
        self._status = ""
        self._work_roster: list[WorkRow] = []
        # (task_id, state) — WorkChanged / D-Bus notify only when this changes.
        self._work_fingerprint: tuple[tuple[int, str], ...] | None = None
        self._draft_parent_id: int = 0
        self._collapsed_task_ids: set[int] = set()

        # Create task
        self._create_open = False
        self._create_title = ""
        self._create_description = ""
        self._create_is_favorite = False
        self._create_kind = TaskKind.TIMED.value
        self._create_mode = TimerMode.STOPWATCH.value
        self._create_hours = 0
        self._create_minutes = 0
        self._create_list_id = LIST_FAVORITES_ID
        self._create_recurrence_kind = RecurrenceKind.NONE.value
        self._create_recurrence_interval = 1
        self._create_recurrence_weekdays = 0

        # Create list
        self._list_dialog_open = False
        self._list_name = ""
        self._list_icon = "📁"
        self._list_description = ""

        # Edit
        self._edit_open = False
        self._edit_task_id = 0
        self._edit_title = ""
        self._edit_description = ""
        self._edit_is_favorite = False
        self._edit_kind = TaskKind.TIMED.value
        self._edit_mode = TimerMode.STOPWATCH.value
        self._edit_hours = 0
        self._edit_minutes = 0
        self._edit_list_id = LIST_FAVORITES_ID
        self._edit_recurrence_kind = RecurrenceKind.NONE.value
        self._edit_recurrence_interval = 1
        self._edit_recurrence_weekdays = 0

        # Delete confirm
        self._delete_open = False
        self._delete_task_id = 0
        self._delete_title = ""
        self._delete_mode = "this_only"  # this_only | cascade
        self._delete_child_count = 0
        self._delete_session_count = 0
        self._delete_own_sessions = 0
        self._delete_tree_sessions = 0

        # Start
        self._start_open = False
        self._start_task_id = 0
        self._start_task_title = ""
        self._start_note = ""

        # Emoji picker
        self._emoji_picker_open = False
        self._emoji_target_list_id = 0
        self._emoji_query = ""

        self._ensure_default_settings()
        self._engine.recover_crash()
        self.refresh_lists()
        self.refresh_tasks()
        self.refresh_work()

    def lists_model(self) -> ListModel:
        return self._lists_model

    def tasks_model(self) -> TaskModel:
        return self._tasks_model

    @Property(QObject, notify=historyDialogChanged)
    def history(self) -> QObject:
        return self._history_model

    @Property(bool, notify=historyDialogOpenChanged)
    def historyDialogOpen(self) -> bool:  # noqa: N802
        return self._history_open

    @Property(bool, notify=historyNoteDialogChanged)
    def historyNoteDialogOpen(self) -> bool:  # noqa: N802
        return self._history_note_open

    @Property(str, notify=historyNoteDialogChanged)
    def historyNoteTaskTitle(self) -> str:  # noqa: N802
        return self._history_note_task_title

    @Property(str, notify=historyNoteDialogChanged)
    def historyNote(self) -> str:  # noqa: N802
        return self._history_note

    @Property(str, notify=historyDialogChanged)
    def historyQuery(self) -> str:  # noqa: N802
        return self._history_query

    @Property(str, notify=historyDialogChanged)
    def historyFrom(self) -> str:  # noqa: N802
        return self._history_from

    @Property(str, notify=historyDialogChanged)
    def historyTo(self) -> str:  # noqa: N802
        return self._history_to

    @Property(str, notify=historyDialogChanged)
    def historyTypeFilter(self) -> str:  # noqa: N802
        return self._history_type_filter

    @Property(str, notify=historyDialogChanged)
    def historySummary(self) -> str:  # noqa: N802
        return self._history_summary

    @Property(str, notify=historyDialogChanged)
    def historyDaySummary(self) -> str:  # noqa: N802
        return self._history_day_summary

    @Property(str, notify=historyDialogChanged)
    def historyTypeSummary(self) -> str:  # noqa: N802
        return self._history_type_summary

    @Property(str, notify=historyDialogChanged)
    def historyFilterSummary(self) -> str:  # noqa: N802
        return self._history_filter_summary

    @Property(bool, notify=historyDialogChanged)
    def historySortAscending(self) -> bool:  # noqa: N802
        """Whether history is currently shown from oldest to newest."""
        return self._history_sort_ascending

    @Property(str, notify=historyDialogChanged)
    def historySortKey(self) -> str:  # noqa: N802
        return self._history_sort_key

    @Property(bool, notify=scheduleDialogChanged)
    def scheduleDialogOpen(self) -> bool:  # noqa: N802
        return self._schedule_open

    @Property(str, notify=scheduleDialogChanged)
    def scheduleTaskTitle(self) -> str:  # noqa: N802
        return self._schedule_task_title

    @Property(str, notify=scheduleDialogChanged)
    def scheduleDate(self) -> str:  # noqa: N802
        return self._schedule_date

    @Property(bool, notify=scheduleDialogChanged)
    def scheduleDateAssigned(self) -> bool:  # noqa: N802
        if not self._schedule_task_id:
            return False
        try:
            selected = date.fromisoformat(self._schedule_date)
        except ValueError:
            return False
        return self._assignments.is_assigned(self._schedule_task_id, selected)

    @Property(bool, notify=sessionNoteDialogChanged)
    def sessionNoteDialogOpen(self) -> bool:  # noqa: N802
        return self._session_note_open

    @Property(str, notify=sessionNoteDialogChanged)
    def sessionNoteTaskTitle(self) -> str:  # noqa: N802
        return self._session_note_task_title

    @Property(str, notify=sessionNoteDialogChanged)
    def sessionNote(self) -> str:  # noqa: N802
        return self._session_note

    @Property(QObject, notify=listsChanged)
    def lists(self) -> QObject:
        return self._lists_model

    @Property(QObject, notify=tasksChanged)
    def tasks(self) -> QObject:
        return self._tasks_model

    @Property(QObject, notify=parentPickerChanged)
    def parentPicker(self) -> QObject:  # noqa: N802
        return self._parent_picker

    @Property(int, notify=parentPickerChanged)
    def draftParentId(self) -> int:  # noqa: N802
        return self._draft_parent_id

    @Property(int, notify=selectionChanged)
    def selectedListId(self) -> int:  # noqa: N802
        return self._selected_list_id

    @Property(str, notify=statusChanged)
    def statusMessage(self) -> str:  # noqa: N802
        return self._status

    # --- create props ---
    @Property(bool, notify=createDialogChanged)
    def createDialogOpen(self) -> bool:  # noqa: N802
        return self._create_open

    @Property(str, notify=createDialogChanged)
    def createTitle(self) -> str:  # noqa: N802
        return self._create_title

    @Property(str, notify=createDialogChanged)
    def createDescription(self) -> str:  # noqa: N802
        return self._create_description

    @Property(bool, notify=createDialogChanged)
    def createIsFavorite(self) -> bool:  # noqa: N802
        return self._create_is_favorite

    @Property(str, notify=createDialogChanged)
    def createKind(self) -> str:  # noqa: N802
        return self._create_kind

    @Property(str, notify=createDialogChanged)
    def createMode(self) -> str:  # noqa: N802
        return self._create_mode

    @Property(int, notify=createDialogChanged)
    def createHours(self) -> int:  # noqa: N802
        return self._create_hours

    @Property(int, notify=createDialogChanged)
    def createMinutes(self) -> int:  # noqa: N802
        return self._create_minutes

    @Property(int, notify=createDialogChanged)
    def createListId(self) -> int:  # noqa: N802
        return self._create_list_id

    @Property(str, notify=createDialogChanged)
    def createRecurrenceKind(self) -> str:  # noqa: N802
        return self._create_recurrence_kind

    @Property(int, notify=createDialogChanged)
    def createRecurrenceInterval(self) -> int:  # noqa: N802
        return self._create_recurrence_interval

    @Property(int, notify=createDialogChanged)
    def createRecurrenceWeekdays(self) -> int:  # noqa: N802
        return self._create_recurrence_weekdays

    @Property(QObject, notify=listsChanged)
    def listPicker(self) -> QObject:  # noqa: N802
        return self._list_picker

    @Property(str, notify=createDialogChanged)
    def createListHint(self) -> str:  # noqa: N802
        if self._create_list_id == LIST_FAVORITES_ID:
            return tr("hint.create_no_group")
        selected = self._lists_repo.get(self._create_list_id)
        if selected is None:
            return ""
        title = list_title(selected.key, selected.name)
        return tr("hint.create_group", title=title)

    # --- create-list props ---
    @Property(bool, notify=listDialogChanged)
    def listDialogOpen(self) -> bool:  # noqa: N802
        return self._list_dialog_open

    @Property(str, notify=listDialogChanged)
    def listName(self) -> str:  # noqa: N802
        return self._list_name

    @Property(str, notify=listDialogChanged)
    def listIcon(self) -> str:  # noqa: N802
        return self._list_icon

    @Property(str, notify=listDialogChanged)
    def listDescription(self) -> str:  # noqa: N802
        return self._list_description

    # --- edit props ---
    @Property(bool, notify=editDialogChanged)
    def editDialogOpen(self) -> bool:  # noqa: N802
        return self._edit_open

    @Property(str, notify=editDialogChanged)
    def editTitle(self) -> str:  # noqa: N802
        return self._edit_title

    @Property(str, notify=editDialogChanged)
    def editDescription(self) -> str:  # noqa: N802
        return self._edit_description

    @Property(str, notify=editDialogChanged)
    def editKind(self) -> str:  # noqa: N802
        return self._edit_kind

    @Property(int, notify=editDialogChanged)
    def editTaskId(self) -> int:  # noqa: N802
        return self._edit_task_id

    @Property(bool, notify=editDialogChanged)
    def editScheduledToday(self) -> bool:  # noqa: N802
        return bool(
            self._edit_task_id and self._assignments.is_assigned(self._edit_task_id, local_today())
        )

    @Property(str, notify=editDialogChanged)
    def editMode(self) -> str:  # noqa: N802
        return self._edit_mode

    @Property(int, notify=editDialogChanged)
    def editHours(self) -> int:  # noqa: N802
        return self._edit_hours

    @Property(int, notify=editDialogChanged)
    def editMinutes(self) -> int:  # noqa: N802
        return self._edit_minutes

    @Property(int, notify=editDialogChanged)
    def editListId(self) -> int:  # noqa: N802
        return self._edit_list_id

    @Property(bool, notify=editDialogChanged)
    def editIsFavorite(self) -> bool:  # noqa: N802
        return self._edit_is_favorite

    @Property(str, notify=editDialogChanged)
    def editRecurrenceKind(self) -> str:  # noqa: N802
        return self._edit_recurrence_kind

    @Property(int, notify=editDialogChanged)
    def editRecurrenceInterval(self) -> int:  # noqa: N802
        return self._edit_recurrence_interval

    @Property(int, notify=editDialogChanged)
    def editRecurrenceWeekdays(self) -> int:  # noqa: N802
        return self._edit_recurrence_weekdays

    @Property(bool, notify=deleteDialogChanged)
    def deleteDialogOpen(self) -> bool:  # noqa: N802
        return self._delete_open

    @Property(str, notify=deleteDialogChanged)
    def deleteTaskTitle(self) -> str:  # noqa: N802
        return self._delete_title

    @Property(str, notify=deleteDialogChanged)
    def deleteMode(self) -> str:  # noqa: N802
        return self._delete_mode

    @Property(int, notify=deleteDialogChanged)
    def deleteChildCount(self) -> int:  # noqa: N802
        return self._delete_child_count

    @Property(int, notify=deleteDialogChanged)
    def deleteSessionCount(self) -> int:  # noqa: N802
        return self._delete_session_count

    @Property(bool, notify=deleteDialogChanged)
    def deleteHasChildren(self) -> bool:  # noqa: N802
        return self._delete_child_count > 0

    @Property(bool, notify=editDialogChanged)
    def editCanRemoveFromGroup(self) -> bool:  # noqa: N802
        if not self._edit_task_id:
            return False
        task = self._tasks_repo.get(self._edit_task_id)
        return task is not None and task.list_id != LIST_FAVORITES_ID

    @Property(bool, notify=editDialogChanged)
    def editCanUnparent(self) -> bool:  # noqa: N802
        if not self._edit_task_id:
            return False
        task = self._tasks_repo.get(self._edit_task_id)
        return task is not None and task.parent_task_id is not None

    # --- start props ---
    @Property(bool, notify=startDialogChanged)
    def startDialogOpen(self) -> bool:  # noqa: N802
        return self._start_open

    @Property(str, notify=startDialogChanged)
    def startTaskTitle(self) -> str:  # noqa: N802
        return self._start_task_title

    @Property(str, notify=startDialogChanged)
    def startNote(self) -> str:  # noqa: N802
        return self._start_note

    @Property(bool, notify=emojiPickerOpenChanged)
    def emojiPickerOpen(self) -> bool:  # noqa: N802
        return self._emoji_picker_open

    @Property(str, notify=emojiQueryChanged)
    def emojiQuery(self) -> str:  # noqa: N802
        return self._emoji_query

    @Property(QObject, notify=emojiPickerOpenChanged)
    def emojiModel(self) -> QObject:  # noqa: N802
        return self._emoji_model

    @Slot(int)
    def selectList(self, list_id: int) -> None:  # noqa: N802
        if list_id == self._selected_list_id:
            return
        self._selected_list_id = list_id
        self.selectionChanged.emit()
        self.refresh_tasks()

    @Slot(int)
    def resumeTask(self, task_id: int) -> None:  # noqa: N802
        """Resume a paused «В работе» task without opening the start dialog."""
        try:
            self._engine.resume(task_id)
        except HierarchyConflictError as exc:
            self._set_status(str(exc))
            return
        self.refresh_tasks()
        self.refresh_work()
        self._set_status(tr("status.started", title=self._task_title(task_id)))

    @Slot(int)
    def pauseTask(self, task_id: int) -> None:  # noqa: N802
        try:
            self._engine.pause(task_id)
        except NoActiveSessionError:
            self._set_status(tr("status.no_session"))
            return
        self.refresh_tasks()
        self.refresh_work()
        self._set_status(tr("status.paused_session", title=self._task_title(task_id)))

    @Slot(int)
    def stopTask(self, task_id: int) -> None:  # noqa: N802
        title = self._task_title(task_id)
        self._engine.stop(task_id)
        self.refresh_tasks()
        self.refresh_work()
        self._set_status(tr("status.stopped", title=title))

    @Slot(int)
    def completeChecklist(self, task_id: int) -> None:  # noqa: N802
        """Record one binary execution without creating a timer session."""
        try:
            task = self._tasks_svc.complete_checklist(int(task_id))
        except (KeyError, ValueError) as exc:
            self._set_status(str(exc))
            return
        self.refresh_tasks()
        self.refresh_work()
        self._set_status(tr("status.completed", title=task.title))

    @Slot(int)
    def toggleChecklist(self, task_id: int) -> None:  # noqa: N802
        """Correct a checklist state without being used for normal execution."""
        try:
            task = self._tasks_svc.toggle_checklist(int(task_id))
        except (KeyError, ValueError) as exc:
            self._set_status(str(exc))
            return
        self.refresh_tasks()
        self.refresh_work()
        status_key = "status.completed" if task.is_completed else "status.uncompleted"
        self._set_status(tr(status_key, title=task.title))

    @Slot(int)
    def toggleTodayAssignment(self, task_id: int) -> None:  # noqa: N802
        try:
            assigned = self._tasks_svc.toggle_today_assignment(
                int(task_id), assigned_date=local_today()
            )
        except (KeyError, ValueError) as exc:
            self._set_status(str(exc))
            return
        self.refresh_tasks()
        self._set_status(
            tr(
                "status.added_today" if assigned else "status.removed_today",
                title=self._task_title(task_id),
            )
        )

    @Slot(int)
    def openScheduleDialog(self, task_id: int) -> None:  # noqa: N802
        task = self._tasks_repo.get(int(task_id))
        if task is None:
            return
        self._schedule_task_id = task.id
        self._schedule_task_title = task.title
        self._schedule_date = local_today().isoformat()
        self._schedule_open = True
        self.scheduleDialogChanged.emit()

    @Slot()
    def closeScheduleDialog(self) -> None:  # noqa: N802
        self._schedule_open = False
        self.scheduleDialogChanged.emit()

    @Slot(str)
    def setScheduleDate(self, value: str) -> None:  # noqa: N802
        try:
            date.fromisoformat(value)
        except ValueError:
            return
        self._schedule_date = value
        self.scheduleDialogChanged.emit()

    @Slot()
    def toggleScheduleDate(self) -> None:  # noqa: N802
        if not self._schedule_task_id:
            return
        selected = date.fromisoformat(self._schedule_date)
        assigned = self._tasks_svc.toggle_today_assignment(
            self._schedule_task_id,
            assigned_date=selected,
        )
        self.refresh_tasks()
        self.scheduleDialogChanged.emit()
        self._set_status(
            tr(
                "status.added_date" if assigned else "status.removed_date",
                title=self._schedule_task_title,
                date=self._schedule_date,
            )
        )

    @Slot(int)
    def openSessionNoteDialog(self, task_id: int) -> None:  # noqa: N802
        session = self._engine.session_for_task(int(task_id))
        task = self._tasks_repo.get(int(task_id))
        if session is None or task is None:
            self._set_status(tr("status.no_session"))
            return
        self._session_note_task_id = task.id
        self._session_note_task_title = task.title
        self._session_note = session.note
        self._session_note_open = True
        self.sessionNoteDialogChanged.emit()

    @Slot()
    def closeSessionNoteDialog(self) -> None:  # noqa: N802
        self._session_note_open = False
        self.sessionNoteDialogChanged.emit()

    @Slot(str)
    def setSessionNote(self, value: str) -> None:  # noqa: N802
        self._session_note = value
        self.sessionNoteDialogChanged.emit()

    @Slot()
    def saveSessionNote(self) -> None:  # noqa: N802
        if not self._session_note_task_id:
            return
        try:
            self._engine.update_note(self._session_note_task_id, self._session_note)
        except NoActiveSessionError:
            self._set_status(tr("status.no_session"))
            return
        self._session_note_open = False
        self.sessionNoteDialogChanged.emit()
        self._set_status(tr("status.session_note_saved"))

    @Slot()
    def openHistory(self) -> None:  # noqa: N802
        self.refresh_history()
        self._history_open = True
        self.historyDialogOpenChanged.emit()

    @Slot()
    def closeHistory(self) -> None:  # noqa: N802
        self._history_open = False
        self.historyDialogOpenChanged.emit()
        if self._history_note_open:
            self._history_note_open = False
            self.historyNoteDialogChanged.emit()

    @Slot(int)
    def openHistoryNoteDialog(self, completion_id: int) -> None:  # noqa: N802
        completion = self._completions.get(int(completion_id))
        if completion is None:
            self._set_status(tr("status.history_not_found"))
            return
        task = self._tasks_repo.get(completion.task_id)
        self._history_note_completion_id = completion.id
        self._history_note_task_title = task.title if task is not None else f"#{completion.task_id}"
        self._history_note = completion.note
        self._history_note_open = True
        self.historyNoteDialogChanged.emit()

    @Slot()
    def closeHistoryNoteDialog(self) -> None:  # noqa: N802
        self._history_note_open = False
        self.historyNoteDialogChanged.emit()

    @Slot(str)
    def setHistoryNote(self, value: str) -> None:  # noqa: N802
        self._history_note = value
        self.historyNoteDialogChanged.emit()

    @Slot()
    def saveHistoryNote(self) -> None:  # noqa: N802
        if not self._history_note_completion_id:
            return
        completion = self._completions.get(self._history_note_completion_id)
        if completion is None:
            self._set_status(tr("status.history_not_found"))
            self.closeHistoryNoteDialog()
            return
        self._completions.update(completion.id, note=self._history_note)
        self.refresh_history()
        self._history_note_open = False
        self.historyNoteDialogChanged.emit()
        self._set_status(tr("status.history_note_saved"))

    @Slot(int)
    def deleteHistory(self, completion_id: int) -> None:  # noqa: N802
        try:
            self._completions.delete(int(completion_id))
        except KeyError as exc:
            self._set_status(str(exc))
            return
        self.refresh_history()
        self._set_status(tr("status.history_deleted"))

    @Slot(str, "QVariantList", result=str)
    @Slot(str, result=str)
    def exportHistory(self, path: str, selected_completion_ids: list[int] | None = None) -> str:  # noqa: N802
        """Export selected history rows, or all currently filtered rows."""
        target = Path(path).expanduser()
        if not target.name:
            return ""
        rows = self._filtered_history()
        if selected_completion_ids:
            selected_ids = {int(completion_id) for completion_id in selected_completion_ids}
            rows = [completion for completion in rows if completion.id in selected_ids]
        exported = HistoryExporter(self._conn).export(target, rows)
        self._set_status(tr("status.history_exported", path=str(exported)))
        return str(exported)

    @Slot(int, result=str)
    def historyRowText(self, completion_id: int) -> str:  # noqa: N802
        """Return one history row as tab-separated clipboard text."""
        completion = self._completions.get(int(completion_id))
        if completion is None:
            return ""
        task = self._tasks_repo.get(completion.task_id)
        ended = (
            completion.ended_at if completion.session_id is not None else completion.completed_at
        )
        values = (
            completion.completion_date.isoformat(),
            task.title if task is not None else f"#{completion.task_id}",
            tr(f"history.kind.{completion.kind.value}"),
            format_duration(completion.duration_seconds)
            if completion.duration_seconds is not None
            else "—",
            self._history_time(completion.started_at),
            self._history_time(ended),
            completion.note,
        )
        return "\t".join(values)

    @Slot(int, result=int)
    def historyIdAt(self, row: int) -> int:  # noqa: N802
        """Return the completion id at the current filtered/sorted row."""
        rows = self._filtered_history()
        index = int(row)
        if not 0 <= index < len(rows):
            return 0
        return rows[index].id

    @Slot(int, str, str, str)
    def updateHistory(
        self, completion_id: int, started_text: str, ended_text: str, note: str
    ) -> None:  # noqa: N802
        completion = self._completions.get(int(completion_id))
        if completion is None:
            self._set_status(tr("status.history_not_found"))
            return
        try:
            if completion.session_id is not None:
                started = self._parse_local_history_time(started_text)
                ended = self._parse_local_history_time(ended_text)
                if started is None or ended is None or ended < started:
                    raise ValueError("Invalid history interval")
                self._completions.replace_intervals(completion.id, [(started, ended)])
                self._completions.update(completion.id, completed_at=ended, note=note)
            else:
                completed_at = self._parse_local_history_time(ended_text or started_text)
                if completed_at is None:
                    raise ValueError("Invalid completion time")
                self._completions.update(
                    completion.id,
                    completed_at=completed_at,
                    note=note,
                )
        except (ValueError, KeyError) as exc:
            self._set_status(str(exc))
            return
        self.refresh_history()
        self._set_status(tr("status.history_saved"))

    def refresh_history(self) -> None:
        rows: list[HistoryRow] = []
        completions = self._filtered_history()
        self._refresh_history_summaries(completions)
        for completion in completions:
            task = self._tasks_repo.get(completion.task_id)
            title = task.title if task is not None else f"#{completion.task_id}"
            rows.append(
                HistoryRow(
                    id=completion.id,
                    task_id=completion.task_id,
                    title=title,
                    kind=(task.kind.value if task is not None else "timed"),
                    completion_kind=tr(f"history.kind.{completion.kind.value}"),
                    completion_date=completion.completion_date.isoformat(),
                    completed_at=self._history_time(completion.completed_at),
                    started_at=self._history_time(completion.started_at),
                    ended_at=self._history_time(
                        completion.ended_at or completion.completed_at
                        if completion.session_id is None
                        else completion.ended_at
                    ),
                    duration=(
                        format_duration(completion.duration_seconds)
                        if completion.duration_seconds is not None
                        else "—"
                    ),
                    note=completion.note,
                    is_timed=completion.session_id is not None,
                )
            )
        self._history_model.reset_items(rows)
        self.historyDialogChanged.emit()

    @Slot()
    def refreshHistory(self) -> None:  # noqa: N802
        self.refresh_history()

    def _refresh_history_summaries(self, completions: list[TaskCompletion]) -> None:
        total_seconds = sum(item.duration_seconds or 0 for item in completions)
        self._history_summary = tr(
            "history.summary",
            count=len(completions),
            duration=format_duration(total_seconds),
        )
        by_day: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for completion in completions:
            day = completion.completion_date.isoformat()
            by_day[day] = by_day.get(day, 0) + 1
            kind = self._history_type_key(completion)
            by_type[kind] = by_type.get(kind, 0) + 1
        self._history_day_summary = tr(
            "history.by_day",
            value=(
                ", ".join(f"{day}: {count}" for day, count in sorted(by_day.items()))
                or tr("history.summary_empty")
            ),
        )
        self._history_type_summary = tr(
            "history.by_type",
            value=(
                ", ".join(
                    f"{tr(f'history.type.{kind}')}: {count}"
                    for kind, count in sorted(by_type.items())
                )
                or tr("history.summary_empty")
            ),
        )
        active_filters: list[str] = []
        if self._history_query.strip():
            active_filters.append(tr("history.filter_task", value=self._history_query.strip()))
        if self._history_from:
            active_filters.append(tr("history.filter_from", value=self._history_from))
        if self._history_to:
            active_filters.append(tr("history.filter_to", value=self._history_to))
        if self._history_type_filter:
            active_filters.append(
                tr(
                    "history.filter_type",
                    value=tr(f"history.type.{self._history_type_filter}"),
                )
            )
        self._history_filter_summary = (
            tr("history.filters_active", value="; ".join(active_filters)) if active_filters else ""
        )

    def _history_type_key(self, completion: TaskCompletion) -> str:
        task = self._tasks_repo.get(completion.task_id)
        if task is not None and task.kind is TaskKind.CHECKLIST:
            return "checklist"
        if completion.session_id is not None:
            session = self._sessions_repo.get(completion.session_id)
            if session is not None and session.target_seconds is not None:
                return "countdown"
        return "stopwatch"

    def _filtered_history(self) -> list[TaskCompletion]:
        query = self._history_query.strip().casefold()
        from_day = self._parse_history_date(self._history_from)
        to_day = self._parse_history_date(self._history_to)
        rows = []
        for completion in self._completions.list_all():
            task = self._tasks_repo.get(completion.task_id)
            title = task.title if task is not None else f"#{completion.task_id}"
            if query and query not in title.casefold():
                continue
            if from_day is not None and completion.completion_date < from_day:
                continue
            if to_day is not None and completion.completion_date > to_day:
                continue
            if (
                self._history_type_filter
                and self._history_type_key(completion) != self._history_type_filter
            ):
                continue
            rows.append(completion)
        rows.sort(
            key=lambda completion: self._history_sort_value(completion, self._history_sort_key),
            reverse=not self._history_sort_ascending,
        )
        return rows

    def _history_sort_value(self, completion: TaskCompletion, sort_key: str) -> tuple[object, int]:
        task = self._tasks_repo.get(completion.task_id)
        title = task.title.casefold() if task is not None else f"#{completion.task_id}"
        empty_time = datetime.min.replace(tzinfo=UTC)
        if sort_key == "task":
            value: object = title
        elif sort_key == "type":
            value = tr(f"history.kind.{completion.kind.value}").casefold()
        elif sort_key == "duration":
            value = completion.duration_seconds if completion.duration_seconds is not None else -1
        elif sort_key == "start":
            value = completion.started_at or empty_time
        elif sort_key == "end":
            value = completion.ended_at or completion.completed_at
        elif sort_key == "note":
            value = completion.note.casefold()
        else:
            value = completion.completion_date
        return value, completion.id

    @Slot(str)
    def setHistoryQuery(self, value: str) -> None:  # noqa: N802
        self._history_query = value
        self.refresh_history()

    @Slot(str)
    def setHistoryFrom(self, value: str) -> None:  # noqa: N802
        self._history_from = value
        self.refresh_history()

    @Slot(str)
    def setHistoryTo(self, value: str) -> None:  # noqa: N802
        self._history_to = value
        self.refresh_history()

    @Slot(str)
    def setHistoryTypeFilter(self, value: str) -> None:  # noqa: N802
        if value not in ("", "checklist", "countdown", "stopwatch"):
            return
        self._history_type_filter = value
        self.refresh_history()

    @Slot()
    def clearHistoryFilters(self) -> None:  # noqa: N802
        self._history_query = ""
        self._history_from = ""
        self._history_to = ""
        self._history_type_filter = ""
        self.refresh_history()

    @Slot()
    def toggleHistorySort(self) -> None:  # noqa: N802
        self._history_sort_ascending = not self._history_sort_ascending
        self.refresh_history()

    @Slot(str)
    def setHistorySort(self, sort_key: str) -> None:  # noqa: N802
        allowed = {"date", "task", "type", "duration", "start", "end", "note"}
        if sort_key not in allowed:
            return
        if sort_key == self._history_sort_key:
            self._history_sort_ascending = not self._history_sort_ascending
        else:
            self._history_sort_key = sort_key
            self._history_sort_ascending = True
        self.refresh_history()

    @staticmethod
    def _parse_history_date(value: str) -> date | None:
        text = value.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def _history_time(value: datetime | None) -> str:
        if value is None:
            return ""
        return value.astimezone().strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def _parse_local_history_time(value: str) -> datetime | None:
        text = value.strip()
        if not text:
            return None
        parsed = datetime.fromisoformat(text.replace(" ", "T"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return parsed

    @Slot()
    def showAllInWork(self) -> None:  # noqa: N802
        self.selectList(LIST_IN_WORK_ID)

    @Slot()
    def tick(self) -> None:
        target_reached = self._handle_target_reached()
        self.refresh_work()
        if target_reached or self._work_repo.list_all():
            self.refresh_tasks()

    @Slot()
    def heartbeat(self) -> None:
        self._engine.heartbeat()

    @Slot(int)
    def toggleExpanded(self, task_id: int) -> None:  # noqa: N802
        tid = int(task_id)
        if tid in self._collapsed_task_ids:
            self._collapsed_task_ids.discard(tid)
        else:
            self._collapsed_task_ids.add(tid)
        self.refresh_tasks()

    @Slot()
    def retranslateUi(self) -> None:  # noqa: N802
        """Re-emit dialog/list signals so QML labels rebuild after language change."""
        self.createDialogChanged.emit()
        self.listDialogChanged.emit()
        self.editDialogChanged.emit()
        self.deleteDialogChanged.emit()
        self.startDialogChanged.emit()
        self.parentPickerChanged.emit()
        self.emojiPickerOpenChanged.emit()
        self.statusChanged.emit()
        self.historyDialogChanged.emit()
        self.historyNoteDialogChanged.emit()
        self.sessionNoteDialogChanged.emit()

    def refresh_lists(self) -> None:
        raw = self._lists_repo.list_all()
        localized = [
            TaskList(
                id=item.id,
                name=list_title(item.key, item.name),
                position=item.position,
                is_system=item.is_system,
                key=item.key,
                icon=item.icon,
                description=("" if item.id in LISTS_WITHOUT_DESCRIPTION else item.description),
            )
            for item in raw
        ]
        self._lists_model.reset_items(localized)
        self._reload_list_picker()
        self.listsChanged.emit()

    def refresh_tasks(self) -> None:
        seed_tasks = seed_tasks_for_list(
            selected_list_id=self._selected_list_id,
            lists_repo=self._lists_repo,
            tasks_repo=self._tasks_repo,
            work_repo=self._work_repo,
            recurrence_repo=self._recurrence_repo,
            assignment_repo=self._assignments,
            completion_repo=self._completions,
        )
        rows = build_task_rows(
            engine=self._engine,
            work_repo=self._work_repo,
            tasks_repo=self._tasks_repo,
            seed_tasks=seed_tasks,
            collapsed_task_ids=self._collapsed_task_ids,
            assignment_repo=self._assignments,
            recurrence_repo=self._recurrence_repo,
            today_occurrence=self._selected_list_id == LIST_TODAY_ID,
        )
        self._tasks_model.reset_items(rows)
        self.tasksChanged.emit()

    def work_roster(self) -> list[WorkRow]:
        """All «В работе» rows (running + paused), for tray and other surfaces."""
        return list(self._work_roster)

    def refresh_work(self) -> None:
        """Refresh roster clocks every call; emit workChanged only on membership/state."""
        rows = build_work_rows(
            engine=self._engine,
            work_repo=self._work_repo,
            tasks_repo=self._tasks_repo,
        )
        fingerprint = tuple((r.task_id, r.state) for r in rows)
        self._work_roster = rows
        if fingerprint != self._work_fingerprint:
            self._work_fingerprint = fingerprint
            self.workChanged.emit()

    def _handle_target_reached(self) -> bool:
        events = self._engine.poll_target_reached()
        for event in events:
            task = self._tasks_repo.get(event.task_id)
            title = task.title if task else f"#{event.task_id}"
            sound = (
                self._settings.get(settings_keys.TIMER_SOUND) or settings_keys.TIMER_SOUND_SYSTEM
            )
            self._notifier.notify_timer_finished(title, sound=sound)
            self._set_status(tr("status.timer_done", title=title))
            # Countdown always stops at zero (manual Stop still works earlier).
            with contextlib.suppress(NoActiveSessionError):
                self._engine.stop(
                    event.task_id,
                    completion_kind=CompletionKind.TARGET_REACHED,
                )
        return bool(events)

    def _ensure_default_settings(self) -> None:
        # Full defaults live in SettingsBridge; keep timer sound for headless/tests.
        if self._settings.get(settings_keys.TIMER_SOUND) is None:
            self._settings.set(settings_keys.TIMER_SOUND, settings_keys.TIMER_SOUND_SYSTEM)

    def _task_title(self, task_id: int) -> str:
        task = self._tasks_repo.get(task_id)
        return task.title if task is not None else f"#{task_id}"

    def _set_status(self, message: str) -> None:
        self._status = message
        self.statusChanged.emit()

    @property
    def engine(self) -> TimerEngine:
        return self._engine
