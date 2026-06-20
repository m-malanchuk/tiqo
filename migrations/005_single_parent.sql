-- Collapse DAG → tree: at most one parent per task.

ALTER TABLE tasks ADD COLUMN parent_task_id INTEGER REFERENCES tasks (id) ON DELETE SET NULL;

-- Keep one parent if several existed (lowest parent id for stability).
UPDATE tasks
SET parent_task_id = (
    SELECT MIN(parent_task_id)
    FROM task_links
    WHERE task_links.child_task_id = tasks.id
)
WHERE EXISTS (
    SELECT 1 FROM task_links WHERE task_links.child_task_id = tasks.id
);

DROP TABLE IF EXISTS task_links;

CREATE INDEX idx_tasks_parent ON tasks (parent_task_id);
