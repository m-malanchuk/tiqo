-- List description + system list «all» (Все задачи).

ALTER TABLE lists ADD COLUMN description TEXT NOT NULL DEFAULT '';

-- Make room at the top for «all»
UPDATE lists SET position = position + 1;

INSERT INTO lists (id, name, position, is_system, key, icon, description) VALUES
    (4, 'all', 0, 1, 'all', '📋', '');
