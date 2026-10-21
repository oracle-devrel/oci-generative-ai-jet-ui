SELECT e.*,
       PREDICTION(BGE_RERANKER USING :query AS FIRST_INPUT,
                  e.content AS SECOND_INPUT) AS rerank_raw,
       CASE WHEN e.deleted_at IS NULL
                  AND e.valid_from <= :at
                  AND (e.valid_until IS NULL OR e.valid_until > :at)
            THEN 'current' ELSE 'historical_or_ineligible' END AS lifecycle
  FROM entity_memory AS OF SCN :scn e
 WHERE (e.user_id IS NULL OR e.user_id = :user_id)
   AND (e.agent_id IS NULL OR e.agent_id = :agent_id)
   AND (e.thread_id IS NULL OR e.thread_id = :thread_id)
 ORDER BY e.subject, e.predicate, e.version, e.id
-- Tenant VPD applies to this table reference, including AS OF SCN.
