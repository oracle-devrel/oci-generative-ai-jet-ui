-- The teachable queries for the video. Run these against a populated agent_memory.
-- Bind :task to the task the agent is about to attempt.

ALTER SESSION SET CURRENT_SCHEMA = CCC;

-- 1) SEMANTIC RECALL — before acting, pull the most relevant past experiences by meaning.
SELECT task, action, outcome, detail,
       VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING(MINILM USING :task AS DATA), COSINE) AS dist
FROM   agent_memory
ORDER  BY dist
FETCH  APPROXIMATE FIRST 5 ROWS ONLY;

-- 2) DON'T REPEAT MISTAKES — the relevant past experiences that FAILED.
SELECT task, action, detail
FROM   agent_memory
WHERE  outcome = 'failure'
ORDER  BY VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING(MINILM USING :task AS DATA), COSINE)
FETCH  APPROXIMATE FIRST 3 ROWS ONLY;

-- 3) THE AUDITABLE FLEX — the agent's track record, plain SQL, no vectors needed.
SELECT * FROM tool_stats ORDER BY success_rate DESC;

-- 4) SECOND-BRAIN DEMO over your CONTENT (not memory): find every version of an idea you've
--    posted, across platforms, by meaning. (Requires embeddings on posts — see README extras.)
-- SELECT platform_id, kind, SUBSTR(caption,1,80) AS preview
-- FROM   posts
-- ORDER  BY VECTOR_DISTANCE(caption_embedding, VECTOR_EMBEDDING(MINILM USING :idea AS DATA), COSINE)
-- FETCH  APPROXIMATE FIRST 10 ROWS ONLY;
