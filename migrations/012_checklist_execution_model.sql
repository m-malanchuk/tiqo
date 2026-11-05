-- Checklist completion is an execution event, not persistent task state.
-- Preserve legacy completed checklist rows before removing the old columns.

INSERT INTO task_completions (
    task_id,
    session_id,
    completed_at,
    completion_date,
    completion_kind,
    note,
    started_at,
    ended_at,
    duration_seconds
)
SELECT
    t.id,
    NULL,
    t.checklist_completed_at,
    date(t.checklist_completed_at, 'localtime'),
    'checklist',
    '',
    NULL,
    NULL,
    NULL
FROM tasks AS t
WHERE t.task_kind = 'checklist'
  AND t.checklist_done = 1
  AND t.checklist_completed_at IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM task_completions AS c
      WHERE c.task_id = t.id
        AND c.session_id IS NULL
        AND c.completion_kind = 'checklist'
        AND c.completed_at = t.checklist_completed_at
  );

ALTER TABLE tasks
    ADD COLUMN prompt_completion_note INTEGER NOT NULL DEFAULT 0
    CHECK (prompt_completion_note IN (0, 1));

ALTER TABLE tasks DROP COLUMN checklist_done;
ALTER TABLE tasks DROP COLUMN checklist_completed_at;
