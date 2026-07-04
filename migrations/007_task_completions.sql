-- Completion events for future calendar/statistics views.
-- A duration completion points to its source session; checklist completions may
-- omit session_id because they are actions, not time intervals.

CREATE TABLE task_completions (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    session_id INTEGER REFERENCES sessions (id) ON DELETE SET NULL,
    completed_at TEXT NOT NULL,
    completion_date TEXT NOT NULL,
    completion_kind TEXT NOT NULL CHECK (
        completion_kind IN ('manual_stop', 'target_reached', 'checklist')
    )
);

CREATE UNIQUE INDEX idx_task_completions_session
    ON task_completions (session_id)
    WHERE session_id IS NOT NULL;
CREATE INDEX idx_task_completions_task_date
    ON task_completions (task_id, completion_date);
