BEGIN;

SELECT id, status
FROM tasks
WHERE status = 'pending'
ORDER BY created_at DESC;

COMMIT;
