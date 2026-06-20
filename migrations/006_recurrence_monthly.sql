-- Allow monthly (day-of-month) recurrence; rebuild table for CHECK change.
CREATE TABLE task_recurrence_new (
    task_id INTEGER PRIMARY KEY REFERENCES tasks (id) ON DELETE CASCADE,
    kind TEXT NOT NULL DEFAULT 'none'
        CHECK (kind IN ('none', 'daily', 'every_n_days', 'weekly', 'monthly')),
    interval INTEGER,
    weekdays_mask INTEGER,
    anchor_date TEXT
);

INSERT INTO task_recurrence_new (task_id, kind, interval, weekdays_mask, anchor_date)
SELECT task_id, kind, interval, weekdays_mask, anchor_date
FROM task_recurrence;

DROP TABLE task_recurrence;
ALTER TABLE task_recurrence_new RENAME TO task_recurrence;
