-- tiqo initial schema (stage 1)

CREATE TABLE lists (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    is_system INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1))
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES lists (id),
    title TEXT NOT NULL,
    default_mode TEXT NOT NULL DEFAULT 'stopwatch'
        CHECK (default_mode IN ('stopwatch', 'countdown')),
    default_target_seconds INTEGER,
    is_favorite INTEGER NOT NULL DEFAULT 0 CHECK (is_favorite IN (0, 1)),
    is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE task_recurrence (
    task_id INTEGER PRIMARY KEY REFERENCES tasks (id) ON DELETE CASCADE,
    kind TEXT NOT NULL DEFAULT 'none'
        CHECK (kind IN ('none', 'daily', 'every_n_days', 'weekly')),
    interval INTEGER,
    weekdays_mask INTEGER,
    anchor_date TEXT
);

CREATE TABLE queue_items (
    task_id INTEGER PRIMARY KEY REFERENCES tasks (id) ON DELETE CASCADE,
    position INTEGER NOT NULL
);

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks (id),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    last_seen_at TEXT NOT NULL,
    target_seconds INTEGER,
    end_reason TEXT CHECK (
        end_reason IS NULL
        OR end_reason IN ('stopped', 'paused', 'crash_recovered')
    )
);

CREATE INDEX idx_sessions_task_id ON sessions (task_id);
CREATE INDEX idx_sessions_open ON sessions (ended_at) WHERE ended_at IS NULL;

CREATE TABLE daily_stats (
    task_id INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    total_seconds INTEGER NOT NULL DEFAULT 0,
    sessions_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (task_id, date)
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- System lists (ids fixed for stable references)
INSERT INTO lists (id, name, position, is_system) VALUES
    (1, 'Избранное', 0, 1),
    (2, 'Сегодня', 1, 1);
