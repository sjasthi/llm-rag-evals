-- Evaluation ownership: rag_responses.user_id and evaluation_runs.user_id
-- (created by schema.sql and initialize_schema()). The Evaluation API only
-- shows a signed-in user their own saved answers, runs and results.
--
-- Ownership is assigned only where it can be proven; nothing is deleted.
--  1. A Chat answer linked to a conversation belongs to that conversation's
--     owner.
--  2. An answer saved inside a test run belongs to the run's owner.
-- Runs and answers saved before accounts existed stay unowned (NULL). They
-- keep all of their contexts, scores and reviews, but no account sees them
-- until an administrator assigns them with:
--     python rag/claim_evaluations.py --username <name>

UPDATE rag_responses response
JOIN conversation_messages message ON message.response_id = response.response_id
JOIN conversations conversation ON conversation.conversation_id = message.conversation_id
SET response.user_id = conversation.user_id
WHERE response.user_id IS NULL
  AND conversation.user_id IS NOT NULL;

UPDATE rag_responses response
JOIN evaluation_runs run ON run.run_id = response.run_id
SET response.user_id = run.user_id
WHERE response.user_id IS NULL
  AND run.user_id IS NOT NULL;
