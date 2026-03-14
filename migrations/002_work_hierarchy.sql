-- Multi-work roster, DAG links, task description, session notes, list i18n keys.

ALTER TABLE lists ADD COLUMN key TEXT;
CREATE UNIQUE INDEX idx_lists_key ON lists (key) WHERE key IS NOT NULL;

UPDATE lists SET key = 'favorites' WHERE id = 1;
UPDATE lists SET key = 'today' WHERE id = 2;
UPDATE lists SET name = 'favorites' WHERE id = 1;
UPDATE lists SET name = 'today' WHERE id = 2;

INSERT INTO lists (id, name, position, is_system, key) VALUES
    (3, 'in_work', 2, 1, 'in_work');

ALTER TABLE tasks ADD COLUMN description TEXT NOT NULL DEFAULT '';

ALTER TABLE sessions ADD COLUMN note TEXT NOT NULL DEFAULT '';

CREATE TABLE task_links (
    parent_task_id INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    child_task_id INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    PRIMARY KEY (parent_task_id, child_task_id),
    CHECK (parent_task_id != child_task_id)
);

CREATE INDEX idx_task_links_child ON task_links (child_task_id);

CREATE TABLE work_items (
    task_id INTEGER PRIMARY KEY REFERENCES tasks (id) ON DELETE CASCADE,
    state TEXT NOT NULL CHECK (state IN ('running', 'paused')),
    position INTEGER NOT NULL DEFAULT 0,
    activated_at TEXT NOT NULL
);
