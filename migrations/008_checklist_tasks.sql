-- Binary checklist tasks have no timer session; their state is stored on tasks.
-- Completion events remain in task_completions for history/statistics.

ALTER TABLE tasks ADD COLUMN task_kind TEXT NOT NULL DEFAULT 'timed'
    CHECK (task_kind IN ('timed', 'checklist'));
ALTER TABLE tasks ADD COLUMN checklist_done INTEGER NOT NULL DEFAULT 0
    CHECK (checklist_done IN (0, 1));
ALTER TABLE tasks ADD COLUMN checklist_completed_at TEXT;

CREATE INDEX idx_tasks_kind ON tasks (task_kind);
