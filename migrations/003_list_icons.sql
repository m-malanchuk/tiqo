-- Per-list emoji icons (user-changeable).

ALTER TABLE lists ADD COLUMN icon TEXT NOT NULL DEFAULT '📁';

UPDATE lists SET icon = '⭐' WHERE key = 'favorites';
UPDATE lists SET icon = '📅' WHERE key = 'today';
UPDATE lists SET icon = '▶' WHERE key = 'in_work';
