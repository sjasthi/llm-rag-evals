-- Multi-user accounts: adds users and conversations.user_id (created by
-- schema.sql and initialize_schema()). Conversations saved before accounts
-- existed have no owner, so no one could open them again; archive them so
-- they never appear in anyone's Recent chats. Their messages and linked
-- rag_responses are kept for research.

UPDATE conversations
SET status = 'archived'
WHERE user_id IS NULL AND status = 'active';
