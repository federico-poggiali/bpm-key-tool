-- A note is always prose: the free-form "type" is gone from the UI. Fold old types into prose.
UPDATE notes SET type = 'prose' WHERE type != 'prose';
