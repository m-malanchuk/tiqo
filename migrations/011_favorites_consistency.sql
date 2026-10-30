-- A task assigned to the Favorites system list must also be marked favorite.
-- Repair rows created by the old "move to Favorites" action.
UPDATE tasks
SET is_favorite = 1
WHERE list_id = 1;
