-- Manual calendar assignments and editable completion-history snapshots.

CREATE TABLE task_assignments (
    task_id INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    assigned_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (task_id, assigned_date)
);

CREATE INDEX idx_task_assignments_date ON task_assignments (assigned_date, task_id);

ALTER TABLE task_completions ADD COLUMN note TEXT NOT NULL DEFAULT '';
ALTER TABLE task_completions ADD COLUMN started_at TEXT;
ALTER TABLE task_completions ADD COLUMN ended_at TEXT;
ALTER TABLE task_completions ADD COLUMN duration_seconds INTEGER;

CREATE TABLE completion_intervals (
    id INTEGER PRIMARY KEY,
    completion_id INTEGER NOT NULL REFERENCES task_completions (id) ON DELETE CASCADE,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    CHECK (ended_at >= started_at)
);

CREATE INDEX idx_completion_intervals_completion
    ON completion_intervals (completion_id, id);

INSERT INTO completion_intervals (completion_id, started_at, ended_at)
SELECT c.id, i.started_at, i.ended_at
FROM task_completions c
JOIN session_intervals i ON i.session_id = c.session_id
WHERE c.session_id IS NOT NULL AND i.ended_at IS NOT NULL;

UPDATE task_completions
SET started_at = (
        SELECT MIN(i.started_at)
        FROM completion_intervals i
        WHERE i.completion_id = task_completions.id
    ),
    ended_at = (
        SELECT MAX(i.ended_at)
        FROM completion_intervals i
        WHERE i.completion_id = task_completions.id
    );

UPDATE task_completions
SET duration_seconds = (
    SELECT COALESCE(SUM(CAST((julianday(i.ended_at) - julianday(i.started_at)) * 86400 AS INTEGER)), 0)
    FROM completion_intervals i
    WHERE i.completion_id = task_completions.id
)
WHERE session_id IS NOT NULL;
