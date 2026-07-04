-- A session is one execution of a task. Work is split into intervals so a
-- pause does not end the session and paused time is never counted.

CREATE TABLE session_intervals (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);

CREATE INDEX idx_session_intervals_session ON session_intervals (session_id, id);
CREATE INDEX idx_session_intervals_open
    ON session_intervals (ended_at)
    WHERE ended_at IS NULL;

INSERT INTO session_intervals (session_id, started_at, ended_at)
SELECT id, started_at, ended_at
FROM sessions;
