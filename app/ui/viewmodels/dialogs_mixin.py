"""Dialog open/close/submit/setters for AppViewModel (create/edit/list/start/delete/emoji)."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Slot

from app.domain.models import (
    LIST_ALL_ID,
    LIST_FAVORITES_ID,
    LIST_IN_WORK_ID,
    LIST_KEY_ALL,
    LIST_TODAY_ID,
    RecurrenceKind,
    TaskKind,
    TaskRecurrence,
    TimerMode,
)
from app.domain.recurrence import weekday_bit
from app.domain.timeutil import local_today
from app.i18n import list_title, tr
from app.services.task_service import TaskService
from app.services.timer_engine import HierarchyConflictError, TimerEngine
from app.storage.assignment_repo import AssignmentRepo
from app.storage.list_repo import ListRepo
from app.storage.recurrence_repo import RecurrenceRepo
from app.storage.session_repo import SessionRepo
from app.storage.task_repo import TaskRepo
from app.ui.viewmodels.emoji_model import EmojiModel
from app.ui.viewmodels.picker_model import PickerModel, PickerRow


class DialogsMixin:
    """Mixin: dialog Slots/helpers. Expects AppViewModel signals + repos on self.

    Qt Properties stay on AppViewModel (notify Signals must live on the QObject).
    """

    _tasks_repo: TaskRepo
    _lists_repo: ListRepo
    _sessions_repo: SessionRepo
    _recurrence_repo: RecurrenceRepo
    _tasks_svc: TaskService
    _assignments: AssignmentRepo
    _engine: TimerEngine
    _emoji_model: EmojiModel
    _parent_picker: PickerModel
    _list_picker: PickerModel

    # These descriptors are declared by the QObject subclass. A mixin cannot
    # express PySide's class-level Signal -> instance-level SignalInstance
    # descriptor relationship, so keep the injected attributes dynamic here.
    createDialogChanged: Any
    listDialogChanged: Any
    editDialogChanged: Any
    deleteDialogChanged: Any
    startDialogChanged: Any
    parentPickerChanged: Any
    selectionChanged: Any
    emojiPickerOpenChanged: Any
    emojiQueryChanged: Any

    if TYPE_CHECKING:

        def _set_status(self, message: str) -> None: ...
        def _task_title(self, task_id: int) -> str: ...
        def refresh_lists(self) -> None: ...
        def refresh_tasks(self) -> None: ...
        def refresh_work(self) -> None: ...
        def selectList(self, list_id: int) -> None: ...

    # ---------- Draft parent (single) ----------
    @Slot(int)
    def setDraftParentId(self, parent_id: int) -> None:  # noqa: N802
        self._set_draft_parent(int(parent_id) if int(parent_id) > 0 else None)
        self._emit_active_dialog_parent_changed()

    # ---------- Create ----------
    @Slot()
    def openCreateDialog(self) -> None:  # noqa: N802
        self._open_create(parent_id=None)

    @Slot(int)
    def openCreateSubtask(self, parent_id: int) -> None:  # noqa: N802
        """Create dialog with parent already selected (подзадача)."""
        self._open_create(parent_id=parent_id if parent_id else None)

    def _open_create(self, *, parent_id: int | None) -> None:
        self._create_open = True
        self._create_title = ""
        self._create_description = ""
        self._create_is_favorite = False
        self._create_kind = TaskKind.TIMED.value
        self._create_mode = TimerMode.STOPWATCH.value
        self._create_hours = 0
        self._create_minutes = 0
        self._create_recurrence_kind = RecurrenceKind.NONE.value
        self._create_recurrence_interval = 1
        self._create_recurrence_weekdays = 0
        if parent_id:
            parent = self._tasks_repo.get(parent_id)
            self._create_list_id = (
                parent.list_id if parent is not None else self._default_create_list_id()
            )
        else:
            self._create_list_id = self._default_create_list_id()
        # Parent comes only from «+» on a card; create dialog has no parent picker.
        self._set_draft_parent(parent_id)
        self._reload_list_picker()
        self.createDialogChanged.emit()

    def _default_create_list_id(self) -> int:
        if self._selected_list_id in (LIST_TODAY_ID, LIST_IN_WORK_ID, LIST_ALL_ID):
            return LIST_FAVORITES_ID
        return self._selected_list_id

    @Slot()
    def closeCreateDialog(self) -> None:  # noqa: N802
        self._create_open = False
        self.createDialogChanged.emit()

    @Slot(str)
    def setCreateTitle(self, value: str) -> None:  # noqa: N802
        self._create_title = value
        self.createDialogChanged.emit()

    @Slot(str)
    def setCreateDescription(self, value: str) -> None:  # noqa: N802
        self._create_description = value
        self.createDialogChanged.emit()

    @Slot(bool)
    def setCreateFavorite(self, value: bool) -> None:  # noqa: N802
        self._create_is_favorite = bool(value)
        self.createDialogChanged.emit()

    @Slot(str)
    def setCreateKind(self, value: str) -> None:  # noqa: N802
        if value not in (TaskKind.TIMED.value, TaskKind.CHECKLIST.value):
            return
        self._create_kind = value
        self.createDialogChanged.emit()

    @Slot(str)
    def setCreateMode(self, value: str) -> None:  # noqa: N802
        if value not in (TimerMode.STOPWATCH.value, TimerMode.COUNTDOWN.value):
            return
        self._create_mode = value
        self.createDialogChanged.emit()

    @Slot(int)
    def setCreateHours(self, value: int) -> None:  # noqa: N802
        self._create_hours = max(0, int(value))
        self.createDialogChanged.emit()

    @Slot(int)
    def setCreateMinutes(self, value: int) -> None:  # noqa: N802
        self._create_minutes = min(59, max(0, int(value)))
        self.createDialogChanged.emit()

    @Slot(int)
    def setCreateListId(self, value: int) -> None:  # noqa: N802
        self._create_list_id = int(value)
        self.createDialogChanged.emit()

    @Slot(str)
    def setCreateRecurrenceKind(self, value: str) -> None:  # noqa: N802
        try:
            kind = RecurrenceKind(value)
        except ValueError:
            return
        self._create_recurrence_kind = kind.value
        self.createDialogChanged.emit()

    @Slot(int)
    def setCreateRecurrenceInterval(self, value: int) -> None:  # noqa: N802
        self._create_recurrence_interval = self._clamp_recurrence_interval(
            self._create_recurrence_kind, int(value)
        )
        self.createDialogChanged.emit()

    @Slot(int)
    def toggleCreateWeekday(self, iso_weekday: int) -> None:  # noqa: N802
        day = int(iso_weekday)
        if not 1 <= day <= 7:
            return
        self._create_recurrence_weekdays ^= weekday_bit(day)
        self.createDialogChanged.emit()

    @Slot()
    def submitCreateDialog(self) -> None:  # noqa: N802
        title = self._create_title.strip()
        if not title:
            self._set_status(tr("status.need_title"))
            return

        list_id = self._create_list_id
        if list_id in (LIST_TODAY_ID, LIST_IN_WORK_ID, LIST_ALL_ID):
            list_id = LIST_FAVORITES_ID

        kind = TaskKind(self._create_kind)
        mode = TimerMode(self._create_mode)
        target: int | None = None
        if kind is TaskKind.CHECKLIST:
            mode = TimerMode.STOPWATCH
        elif mode is TimerMode.COUNTDOWN:
            target = self._create_hours * 3600 + self._create_minutes * 60
            if target <= 0:
                self._set_status(tr("status.need_duration"))
                return

        task = self._tasks_repo.create(
            list_id,
            title,
            description=self._create_description.strip(),
            kind=kind,
            default_mode=mode,
            default_target_seconds=target,
            is_favorite=self._create_is_favorite,
        )
        self._tasks_svc.set_parent(
            task.id, self._draft_parent_id if self._draft_parent_id else None
        )
        self._recurrence_repo.upsert(
            self._draft_rule(
                task.id,
                self._create_recurrence_kind,
                self._create_recurrence_interval,
                self._create_recurrence_weekdays,
            )
        )

        # Stay on Today so a newly due task is visible; leave In Work for Favorites.
        if self._selected_list_id == LIST_IN_WORK_ID:
            self._selected_list_id = LIST_FAVORITES_ID
            self.selectionChanged.emit()
        self._create_open = False
        self.createDialogChanged.emit()
        self.refresh_tasks()
        self._set_status(tr("status.created", title=title))

    # ---------- Create list ----------
    @Slot()
    def openCreateListDialog(self) -> None:  # noqa: N802
        self._list_dialog_open = True
        self._list_name = ""
        self._list_icon = "📁"
        self._list_description = ""
        self.listDialogChanged.emit()

    @Slot()
    def closeCreateListDialog(self) -> None:  # noqa: N802
        self._list_dialog_open = False
        self.listDialogChanged.emit()

    @Slot(str)
    def setListName(self, value: str) -> None:  # noqa: N802
        self._list_name = value
        self.listDialogChanged.emit()

    @Slot(str)
    def setListDescription(self, value: str) -> None:  # noqa: N802
        self._list_description = value
        self.listDialogChanged.emit()

    @Slot()
    def submitCreateListDialog(self) -> None:  # noqa: N802
        name = self._list_name.strip()
        if not name:
            self._set_status(tr("status.need_list_name"))
            return
        created = self._lists_repo.create(
            name,
            icon=self._list_icon.strip() or "📁",
            description=self._list_description.strip(),
        )
        self._list_dialog_open = False
        self.listDialogChanged.emit()
        self.refresh_lists()
        self.selectList(created.id)
        self._set_status(tr("status.group_created", title=name))

    # ---------- Edit ----------
    @Slot(int)
    def openEditDialog(self, task_id: int) -> None:  # noqa: N802
        task = self._tasks_repo.get(task_id)
        if task is None:
            return
        self._edit_open = True
        self._edit_task_id = task.id
        self._edit_title = task.title
        self._edit_description = task.description
        self._edit_is_favorite = task.is_favorite
        self._edit_kind = task.kind.value
        self._edit_mode = task.default_mode.value
        seconds = task.default_target_seconds or 0
        self._edit_hours = seconds // 3600
        self._edit_minutes = (seconds % 3600) // 60
        self._edit_list_id = task.list_id
        rule = self._recurrence_repo.get(task.id)
        if rule is None:
            self._edit_recurrence_kind = RecurrenceKind.NONE.value
            self._edit_recurrence_interval = 1
            self._edit_recurrence_weekdays = 0
        else:
            self._edit_recurrence_kind = rule.kind.value
            self._edit_recurrence_interval = int(rule.interval) if rule.interval is not None else 1
            mask = int(rule.weekdays_mask) if rule.weekdays_mask is not None else 0
            if rule.kind is RecurrenceKind.WEEKLY and mask == 0:
                mask = weekday_bit(local_today().isoweekday())
            self._edit_recurrence_weekdays = mask
        self._set_draft_parent(task.parent_task_id)
        self._reload_parent_picker_for_edit(task.id)
        self._reload_list_picker()
        self.editDialogChanged.emit()
        self.parentPickerChanged.emit()

    @Slot()
    def closeEditDialog(self) -> None:  # noqa: N802
        self._edit_open = False
        self.editDialogChanged.emit()

    @Slot(str)
    def setEditTitle(self, value: str) -> None:  # noqa: N802
        self._edit_title = value
        self.editDialogChanged.emit()

    @Slot(str)
    def setEditDescription(self, value: str) -> None:  # noqa: N802
        self._edit_description = value
        self.editDialogChanged.emit()

    @Slot(bool)
    def setEditFavorite(self, value: bool) -> None:  # noqa: N802
        self._edit_is_favorite = bool(value)
        self.editDialogChanged.emit()

    @Slot(str)
    def setEditKind(self, value: str) -> None:  # noqa: N802
        if value not in (TaskKind.TIMED.value, TaskKind.CHECKLIST.value):
            return
        self._edit_kind = value
        self.editDialogChanged.emit()

    @Slot()
    def toggleEditTodayAssignment(self) -> None:  # noqa: N802
        if not self._edit_task_id:
            return
        assigned = self._tasks_svc.toggle_today_assignment(
            self._edit_task_id,
            assigned_date=local_today(),
        )
        self.editDialogChanged.emit()
        self.refresh_tasks()
        self._set_status(
            tr(
                "status.added_today" if assigned else "status.removed_today",
                title=self._edit_title,
            )
        )

    @Slot(str)
    def setEditMode(self, value: str) -> None:  # noqa: N802
        if value not in (TimerMode.STOPWATCH.value, TimerMode.COUNTDOWN.value):
            return
        self._edit_mode = value
        self.editDialogChanged.emit()

    @Slot(int)
    def setEditHours(self, value: int) -> None:  # noqa: N802
        self._edit_hours = max(0, int(value))
        self.editDialogChanged.emit()

    @Slot(int)
    def setEditMinutes(self, value: int) -> None:  # noqa: N802
        self._edit_minutes = min(59, max(0, int(value)))
        self.editDialogChanged.emit()

    @Slot(int)
    def setEditListId(self, value: int) -> None:  # noqa: N802
        """Move the edited task into a group immediately (any task/subtask)."""
        lid = int(value)
        if lid <= 0 or lid in (LIST_TODAY_ID, LIST_IN_WORK_ID, LIST_ALL_ID):
            return
        if not self._edit_task_id:
            return
        self._edit_list_id = lid
        task = self._tasks_repo.get(self._edit_task_id)
        if task is None:
            return
        if task.list_id != lid:
            self._tasks_repo.update(self._edit_task_id, list_id=lid)
            group = self._lists_repo.get(lid)
            group_title = list_title(group.key, group.name) if group else str(lid)
            self.refresh_tasks()
            self._set_status(tr("status.moved_to_group", title=task.title, group=group_title))
        self.editDialogChanged.emit()

    @Slot(str)
    def setEditRecurrenceKind(self, value: str) -> None:  # noqa: N802
        try:
            kind = RecurrenceKind(value)
        except ValueError:
            return
        self._edit_recurrence_kind = kind.value
        self.editDialogChanged.emit()

    @Slot(int)
    def setEditRecurrenceInterval(self, value: int) -> None:  # noqa: N802
        self._edit_recurrence_interval = self._clamp_recurrence_interval(
            self._edit_recurrence_kind, int(value)
        )
        self.editDialogChanged.emit()

    @Slot(int)
    def toggleEditWeekday(self, iso_weekday: int) -> None:  # noqa: N802
        day = int(iso_weekday)
        if not 1 <= day <= 7:
            return
        self._edit_recurrence_weekdays ^= weekday_bit(day)
        self.editDialogChanged.emit()

    @Slot()
    def submitEditDialog(self) -> None:  # noqa: N802
        title = self._edit_title.strip()
        if not title or not self._edit_task_id:
            self._set_status(tr("status.need_title"))
            return
        kind = TaskKind(self._edit_kind)
        mode = TimerMode(self._edit_mode)
        target: int | None = None
        if kind is TaskKind.CHECKLIST:
            mode = TimerMode.STOPWATCH
        elif mode is TimerMode.COUNTDOWN:
            target = self._edit_hours * 3600 + self._edit_minutes * 60
            if target <= 0:
                self._set_status(tr("status.need_duration"))
                return
        list_id = self._edit_list_id
        if list_id in (LIST_TODAY_ID, LIST_IN_WORK_ID, LIST_ALL_ID):
            list_id = LIST_FAVORITES_ID
        self._tasks_repo.update(
            self._edit_task_id,
            title=title,
            description=self._edit_description.strip(),
            kind=kind,
            default_mode=mode,
            default_target_seconds=target,
            update_target=True,
            list_id=list_id,
            is_favorite=self._edit_is_favorite,
        )
        self._tasks_svc.set_parent(
            self._edit_task_id,
            self._draft_parent_id if self._draft_parent_id else None,
        )
        self._recurrence_repo.upsert(
            self._draft_rule(
                self._edit_task_id,
                self._edit_recurrence_kind,
                self._edit_recurrence_interval,
                self._edit_recurrence_weekdays,
            )
        )
        self._edit_open = False
        self.editDialogChanged.emit()
        self.refresh_tasks()
        self._set_status(tr("status.saved", title=title))

    @Slot()
    def removeEditTaskFromGroup(self) -> None:  # noqa: N802
        """Remove the task's group without changing its Favorites flag."""
        if not self._edit_task_id:
            return
        task = self._tasks_repo.get(self._edit_task_id)
        if task is None or task.list_id == LIST_FAVORITES_ID:
            return
        self._tasks_repo.update(
            self._edit_task_id,
            list_id=LIST_FAVORITES_ID,
        )
        self._edit_open = False
        self.editDialogChanged.emit()
        self.refresh_tasks()
        self._set_status(tr("status.removed_from_group", title=task.title))

    @Slot()
    def unparentEditTask(self) -> None:  # noqa: N802
        """Clear parent — task becomes a root in the hierarchy."""
        if not self._edit_task_id:
            return
        task = self._tasks_repo.get(self._edit_task_id)
        if task is None or task.parent_task_id is None:
            return
        self._tasks_svc.set_parent(self._edit_task_id, None)
        self._set_draft_parent(None)
        self._reload_parent_picker_for_edit(self._edit_task_id)
        self.editDialogChanged.emit()
        self.parentPickerChanged.emit()
        self.refresh_tasks()
        self._set_status(tr("status.unparented", title=task.title))

    # ---------- Delete ----------
    @Slot()
    def requestDeleteTask(self) -> None:  # noqa: N802
        """Open delete confirmation for the task currently in the edit dialog."""
        if not self._edit_task_id:
            return
        task = self._tasks_repo.get(self._edit_task_id)
        if task is None:
            return
        descendants = self._tasks_repo.descendant_ids(task.id)
        self._delete_task_id = task.id
        self._delete_title = task.title
        self._delete_mode = "this_only"
        self._delete_child_count = len(descendants)
        own_sessions = self._sessions_repo.count_for_task(task.id)
        tree_sessions = own_sessions
        for child_id in descendants:
            tree_sessions += self._sessions_repo.count_for_task(child_id)
        self._delete_own_sessions = own_sessions
        self._delete_tree_sessions = tree_sessions
        self._delete_session_count = own_sessions
        self._delete_open = True
        self.deleteDialogChanged.emit()

    @Slot()
    def closeDeleteDialog(self) -> None:  # noqa: N802
        self._delete_open = False
        self.deleteDialogChanged.emit()

    @Slot(str)
    def setDeleteMode(self, value: str) -> None:  # noqa: N802
        if value not in ("this_only", "cascade"):
            return
        self._delete_mode = value
        self._delete_session_count = (
            self._delete_tree_sessions if value == "cascade" else self._delete_own_sessions
        )
        self.deleteDialogChanged.emit()

    @Slot()
    def confirmDeleteTask(self) -> None:  # noqa: N802
        if not self._delete_task_id:
            return
        task_id = self._delete_task_id
        title = self._delete_title
        mode = self._delete_mode
        # Stop tracking if this task (or cascade targets) are running.
        targets = {task_id}
        if mode == "cascade":
            targets |= self._tasks_repo.descendant_ids(task_id)
        for tid in targets:
            if self._engine.open_session_for(tid) is not None:
                with contextlib.suppress(Exception):
                    self._engine.stop(tid)
        try:
            self._tasks_svc.delete_task(task_id, mode=mode)
        except (ValueError, KeyError) as exc:
            self._set_status(str(exc))
            return
        self._delete_open = False
        self._edit_open = False
        self._delete_task_id = 0
        self.deleteDialogChanged.emit()
        self.editDialogChanged.emit()
        self.refresh_tasks()
        self.refresh_work()
        self._set_status(tr("status.deleted", title=title))

    # ---------- Start ----------
    @Slot(int)
    def startTask(self, task_id: int) -> None:  # noqa: N802
        """Open start dialog; tracking begins only after confirmStart."""
        task = self._tasks_repo.get(task_id)
        if task is None:
            return
        latest = self._sessions_repo.latest_for_task(task_id)
        self._start_open = True
        self._start_task_id = task_id
        self._start_task_title = task.title
        self._start_note = latest.note if latest else ""
        self._set_draft_parent(task.parent_task_id)
        self.startDialogChanged.emit()

    @Slot()
    def closeStartDialog(self) -> None:  # noqa: N802
        self._start_open = False
        self.startDialogChanged.emit()

    @Slot(str)
    def setStartNote(self, value: str) -> None:  # noqa: N802
        self._start_note = value
        self.startDialogChanged.emit()

    @Slot()
    def confirmStart(self) -> None:  # noqa: N802
        if not self._start_task_id:
            return
        self._tasks_svc.set_parent(
            self._start_task_id,
            self._draft_parent_id if self._draft_parent_id else None,
        )
        try:
            self._engine.start(
                self._start_task_id,
                use_task_default=True,
                note=self._start_note.strip(),
            )
        except HierarchyConflictError as exc:
            self._set_status(str(exc))
            return
        self._start_open = False
        self.startDialogChanged.emit()
        self.refresh_tasks()
        self.refresh_work()
        self._set_status(tr("status.started", title=self._task_title(self._start_task_id)))

    # ---------- Emoji picker ----------
    @Slot(int)
    def openEmojiPicker(self, list_id: int) -> None:  # noqa: N802
        self._emoji_target_list_id = int(list_id)
        self._emoji_query = ""
        self._emoji_model.set_query("")
        self._emoji_picker_open = True
        self.emojiQueryChanged.emit()
        self.emojiPickerOpenChanged.emit()

    @Slot()
    def openListEmojiPicker(self) -> None:  # noqa: N802
        """Emoji picker for create-list dialog (no existing list target)."""
        self._emoji_target_list_id = -1
        self._emoji_query = ""
        self._emoji_model.set_query("")
        self._emoji_picker_open = True
        self.emojiQueryChanged.emit()
        self.emojiPickerOpenChanged.emit()

    @Slot()
    def closeEmojiPicker(self) -> None:  # noqa: N802
        if not self._emoji_picker_open:
            return
        self._emoji_picker_open = False
        self.emojiPickerOpenChanged.emit()

    @Slot(str)
    def setEmojiQuery(self, value: str) -> None:  # noqa: N802
        self._emoji_query = value
        self._emoji_model.set_query(value)
        self.emojiQueryChanged.emit()

    @Slot(str)
    def chooseEmoji(self, glyph: str) -> None:  # noqa: N802
        if self._list_dialog_open:
            self._list_icon = glyph
            self._emoji_picker_open = False
            self.emojiPickerOpenChanged.emit()
            self.listDialogChanged.emit()
            return
        if self._emoji_target_list_id <= 0:
            return
        self._lists_repo.set_icon(self._emoji_target_list_id, glyph)
        self._emoji_picker_open = False
        self.emojiPickerOpenChanged.emit()
        self.refresh_lists()

    # ---------- Shared dialog helpers ----------
    def _set_draft_parent(self, parent_id: int | None) -> None:
        self._draft_parent_id = int(parent_id) if parent_id else 0
        self.parentPickerChanged.emit()

    def _emit_active_dialog_parent_changed(self) -> None:
        if self._create_open:
            self.createDialogChanged.emit()
        if self._edit_open:
            self.editDialogChanged.emit()
        if self._start_open:
            self.startDialogChanged.emit()

    def _reload_parent_picker_for_edit(self, task_id: int) -> None:
        """Parents you may assign: ancestors (move up) or, if root, any non-descendant."""
        rows = [
            PickerRow(id=0, title=tr("parent.none")),
        ]
        ancestors = self._tasks_repo.ancestor_ids(task_id)
        if ancestors:
            # Nested task: only nodes above in the tree (внутрь/вверх по ветке).
            for aid in sorted(ancestors):
                task = self._tasks_repo.get(aid)
                if task is not None:
                    rows.append(PickerRow(id=task.id, title=task.title))
        else:
            # Root: can place inside any other branch (not self/descendants).
            excluded = {task_id, *self._tasks_repo.descendant_ids(task_id)}
            for task in self._tasks_repo.list_all():
                if task.id in excluded:
                    continue
                rows.append(PickerRow(id=task.id, title=task.title))
        self._parent_picker.reset_items(rows)
        self.parentPickerChanged.emit()

    def _reload_list_picker(self) -> None:
        """No-group sentinel + user lists (exclude virtual system lists)."""
        excluded = {LIST_TODAY_ID, LIST_IN_WORK_ID, LIST_ALL_ID}
        rows: list[PickerRow] = [
            PickerRow(id=LIST_FAVORITES_ID, title=tr("list.no_group")),
        ]
        for item in self._lists_repo.list_all():
            if item.id in excluded or item.id == LIST_FAVORITES_ID or item.key == LIST_KEY_ALL:
                continue
            title = list_title(item.key, item.name)
            rows.append(PickerRow(id=item.id, title=title))
        self._list_picker.reset_items(rows)

    @staticmethod
    def _clamp_recurrence_interval(kind: str, value: int) -> int:
        if kind == RecurrenceKind.MONTHLY.value:
            return min(31, max(1, value))
        if kind == RecurrenceKind.EVERY_N_DAYS.value:
            return min(365, max(1, value))
        return max(1, value)

    def _draft_rule(self, task_id: int, kind: str, interval: int, weekdays: int) -> TaskRecurrence:
        try:
            rk = RecurrenceKind(kind)
        except ValueError:
            rk = RecurrenceKind.NONE
        if rk is RecurrenceKind.NONE:
            return TaskRecurrence(task_id=task_id, kind=rk)
        if rk is RecurrenceKind.DAILY:
            return TaskRecurrence(task_id=task_id, kind=rk)
        if rk is RecurrenceKind.EVERY_N_DAYS:
            n = max(1, int(interval))
            existing = self._recurrence_repo.get(task_id)
            if (
                existing is not None
                and existing.kind is RecurrenceKind.EVERY_N_DAYS
                and existing.anchor_date is not None
            ):
                anchor = existing.anchor_date
            else:
                anchor = local_today()
            return TaskRecurrence(task_id=task_id, kind=rk, interval=n, anchor_date=anchor)
        if rk is RecurrenceKind.WEEKLY:
            mask = int(weekdays)
            if mask == 0:
                mask = weekday_bit(local_today().isoweekday())
            return TaskRecurrence(task_id=task_id, kind=rk, weekdays_mask=mask)
        if rk is RecurrenceKind.MONTHLY:
            day = min(31, max(1, int(interval)))
            return TaskRecurrence(task_id=task_id, kind=rk, interval=day)
        return TaskRecurrence(task_id=task_id, kind=RecurrenceKind.NONE)
