"""Original notebook seed payloads. Stable IDs and dates make repeated runs safe.
Sources are recorded in source_provenance.json. No teardown or erasure cells run.
"""
import hashlib,json,uuid
from datetime import datetime,timezone
TENANT_ACME="acme"
USER_ID="user:jane@acme.com"
AGENT_ID="agent:support_v1"
def sha256(text):return hashlib.sha256(text.encode()).hexdigest()

def seed_schema(conn,cur):
    cur.execute("select count(*) from guideline_memory where id=:id",id="ctxseed_69186c85403b46d0dd54460d")
    if cur.fetchone()[0]:return {"status":"already seeded"}
    counter=0
    def new_id(prefix):
        nonlocal counter
        counter+=1
        return "ctxseed_"+hashlib.sha256(f"seed_schema:{prefix}:{counter}".encode()).hexdigest()[:24]
    now = datetime(2026,7,1)

    # Guideline: tenant-wide refund threshold for Acme.
    gid = new_id("gl")
    cur.execute("""
    INSERT INTO guideline_memory (
      id, tenant_id, guideline_key, guideline_value,
      version, valid_from, written_by, created_at
    ) VALUES (
      :id, :tenant_id, 'refund_threshold',
      JSON('{ "max_auto_approve_usd": 500, "min_confidence": 0.6 }'),
      1, :now, 'admin:acme', :now
    )
    """, id=gid, tenant_id=TENANT_ACME, now=now)

    # Persona: Jane prefers terse responses.
    pid = new_id("pr")
    cur.execute("""
    INSERT INTO persona_memory (
      id, tenant_id, user_id, persona_key, persona_value,
      confidence, written_by, valid_from, created_at
    ) VALUES (
      :id, :tenant_id, :user_id, 'verbosity',
      JSON('{ "value": "terse" }'),
      0.95, 'user', :now, :now
    )
    """, id=pid, tenant_id=TENANT_ACME, user_id=USER_ID, now=now)

    # Entities: two facts with embeddings.
    def insert_entity(subject, predicate, content, source_event_id):
        eid = new_id("ent")
        cur.execute("""
        INSERT INTO entity_memory (
          id, tenant_id, user_id,
          subject, predicate, content, content_hash, content_json,
          embedding, confidence, written_by, source_event_id, version,
          valid_from, created_at
        ) VALUES (
          :id, :tenant_id, :user_id,
          :subject, :predicate, :content, :content_hash,
          JSON('{ "entity_type": "product" }'),
          VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :content_for_embed AS DATA),
          0.95, 'agent:support_v1', :source_event_id, 1,
          :now, :now
        )
        """, id=eid, tenant_id=TENANT_ACME, user_id=USER_ID,
             subject=subject, predicate=predicate,
             content=content, content_hash=sha256(content),
             content_for_embed=content,
             source_event_id=source_event_id, now=now)
        return eid

    ev1 = new_id("evt")
    ev2 = new_id("evt")
    ent_webhook = insert_entity(
        "product:stripe", "webhook_signing",
        "Stripe webhooks are signed with HMAC-SHA256 over the raw request body.",
        ev1,
    )
    ent_rate = insert_entity(
        "product:stripe", "rate_limits",
        "Stripe API rate limits: 100 read req/s and 25 write req/s per account.",
        ev2,
    )

    # Two conversation events (the source side of the provenance link).
    def insert_conv_event(event_id, turn_index, event_type, role, payload):
        cur.execute("""
        INSERT INTO conversation_memory (
          event_id, tenant_id, user_id, thread_id, run_id,
          turn_index, event_type, role, payload, created_at
        ) VALUES (
          :event_id, :tenant_id, :user_id, 'thread_demo', 'run_demo',
          :turn_index, :event_type, :role, JSON(:payload), :now
        )
        """, event_id=event_id, tenant_id=TENANT_ACME, user_id=USER_ID,
             turn_index=turn_index, event_type=event_type, role=role,
             payload=payload, now=now)

    insert_conv_event(ev1, 1, "user_msg",  "user",
                      '{ "text": "How are Stripe webhooks signed?" }')
    insert_conv_event(ev2, 2, "model_msg", "assistant",
                      '{ "text": "HMAC-SHA256 over the raw request body." }')

    # Summarization: one distilled prior-task episode (with an embedding for retrieval).
    sum_id = new_id("sum")
    sum_text = ("Resolved a Stripe webhook signature mismatch after the customer "
                "rotated their signing secret; redeployed with the new env var.")
    cur.execute("""
    INSERT INTO summarization_memory (
      id, tenant_id, user_id, task_type, title, summary,
      outcome, embedding, confidence, written_by, source_event_id,
      version, valid_from, completed_at, created_at
    ) VALUES (
      :id, :tenant_id, :user_id, 'support_case',
      'Stripe webhook signature mismatch after secret rotation',
      :summary, 'resolved',
      VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :summary AS DATA),
      0.9, 'agent:support_v1', 'run_demo', 1, :now, :now, :now
    )
    """, id=sum_id, tenant_id=TENANT_ACME, user_id=USER_ID, summary=sum_text, now=now)

    # Toolbox: one tenant-wide tool definition (enumerated, like guidelines).
    tb_id = new_id("tb")
    cur.execute("""
    INSERT INTO toolbox_memory (
      id, tenant_id, tool_name, tool_schema, usage_notes,
      version, valid_from, written_by, created_at
    ) VALUES (
      :id, :tenant_id, 'issue_refund',
      JSON('{ "type": "object", "properties": { "amount_usd": {"type": "number"}, "reason": {"type": "string"} } }'),
      'Issue a customer refund. Requires manager approval above the refund_threshold policy.',
      1, :now, 'admin:acme', :now
    )
    """, id=tb_id, tenant_id=TENANT_ACME, now=now)

    # Workflow: one tenant-wide learned procedure, ranked by description similarity.
    wf_id = new_id("wf")
    wf_desc = "Diagnose a failing Stripe webhook: check signature, verify the signing secret, confirm the endpoint URL."
    cur.execute("""
    INSERT INTO workflow_memory (
      id, tenant_id, workflow_name, description, steps,
      success_count, failure_count, embedding, confidence,
      version, valid_from, written_by, created_at
    ) VALUES (
      :id, :tenant_id, 'diagnose_webhook_failure', :description,
      JSON('["check Stripe-Signature header", "compare dashboard secret to env var", "redeploy", "verify delivery"]'),
      7, 1,
      VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :description AS DATA),
      0.85, 1, :now, 'agent:support_v1', :now
    )
    """, id=wf_id, tenant_id=TENANT_ACME, description=wf_desc, now=now)

    # Knowledge base: one tenant-wide document plus a single embedded chunk.
    kb_doc_id = new_id("kbd")
    cur.execute("""
    INSERT INTO knowledge_base_document (
      id, tenant_id, collection, title, source_uri, source_type,
      ingested_at, ingested_by, version, valid_from, created_at
    ) VALUES (
      :id, :tenant_id, 'product-docs',
      'Stripe Webhook Integration Guide',
      's3://acme-kb/product-docs/stripe-webhook-guide.md',   -- pointer, not the bytes
      'markdown',
      :now, 'admin:acme', 1, :now, :now
    )
    """, id=kb_doc_id, tenant_id=TENANT_ACME, now=now)

    kb_chunk_text = ("To verify a Stripe webhook, compute HMAC-SHA256 over the raw request body "
                     "using your signing secret and compare it to the Stripe-Signature header.")
    cur.execute("""
    INSERT INTO knowledge_base_chunk (
      id, tenant_id, document_id, chunk_index, content, embedding, created_at
    ) VALUES (
      :id, :tenant_id, :doc_id, 0, :content,
      VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :content AS DATA), :now
    )
    """, id=new_id("kbc"), tenant_id=TENANT_ACME, doc_id=kb_doc_id,
         content=kb_chunk_text, now=now)

    conn.commit()
    print(f"Seeded: 1 guideline, 1 persona, 2 entities, 1 summarization, "
          f"1 toolbox, 1 workflow, 1 KB doc (+1 chunk), "
          f"2 conversation events for tenant={TENANT_ACME!r}.")

def seed_two_layer(conn,cur):
    cur.execute("select count(*) from knowledge_base_document where id=:id",id="ctxseed_94bfffc3bc6cbcef58b29e24")
    if cur.fetchone()[0]:return {"status":"already seeded"}
    counter=0
    def new_id(prefix):
        nonlocal counter
        counter+=1
        return "ctxseed_"+hashlib.sha256(f"seed_two_layer:{prefix}:{counter}".encode()).hexdigest()[:24]
    # The paper the fact came from (a pointer + metadata; the PDF stays in object storage).
    kb_doc_id = new_id("kbd")
    cur.execute("""
    INSERT INTO knowledge_base_document (id, tenant_id, collection, title, source_uri, source_type,
                                         ingested_at, ingested_by, version, valid_from, created_at)
    VALUES (:id, :t, 'benchmarks',
            'Helios-RAG: A Retrieval-Augmented Model for Open-Domain QA (with erratum)',
            's3://acme-kb/papers/helios-rag.pdf', 'pdf', TIMESTAMP '2026-07-01 00:00:00', 'admin:acme', 1,
            TIMESTAMP '2026-07-01 00:00:00', TIMESTAMP '2026-07-01 00:00:00')
    """, id=kb_doc_id, t=TENANT_ACME)

    # The source event that asserted the fact.
    ev1 = new_id("evt")
    cur.execute("""
    INSERT INTO conversation_memory (event_id, tenant_id, user_id, thread_id, run_id,
                                     turn_index, event_type, role, payload, created_at)
    VALUES (:e, :t, :u, 'thread_demo', 'run_demo', 1, 'model_msg', 'assistant',
            JSON('{ "text": "Helios-RAG scores 0.92 nDCG@10 on BEIR." }'), TIMESTAMP '2026-07-01 00:00:00')
    """, e=ev1, t=TENANT_ACME, u=USER_ID)

    # The canonical fact + its inline embedding, in one statement.
    ent_v1 = new_id("ent")
    content_v1 = "Helios-RAG achieves 0.92 nDCG@10 on the BEIR benchmark."
    cur.execute("""
    INSERT INTO entity_memory (
      id, tenant_id, user_id, subject, predicate, content, content_hash, content_json,
      embedding, confidence, written_by, source_event_id, version, valid_from, created_at
    ) VALUES (
      :id, :t, :u, 'model:helios-rag', 'beir_ndcg10', :c, :h,
      JSON('{ "entity_type": "benchmark_result", "source_document_id": "' || :doc || '" }'),
      VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :c2 AS DATA),
      0.95, 'agent:research_v1', :ev, 1, TIMESTAMP '2026-07-01 00:00:00', TIMESTAMP '2026-07-01 00:00:00'
    )
    """, id=ent_v1, t=TENANT_ACME, u=USER_ID, c=content_v1, h=sha256(content_v1),
         doc=kb_doc_id, c2=content_v1, ev=ev1)
    conn.commit()

    cur.execute("""
    SELECT version, SUBSTR(content,1,52) AS content,
           CASE WHEN embedding IS NULL THEN 'no' ELSE 'yes' END AS has_embedding
      FROM entity_memory WHERE id = :id
    """, id=ent_v1)
    r = cur.fetchone()
    print(f"Seeded fact v{r[0]}: {r[1]!r}  | inline embedding present: {r[2]}")
    corr_ev = new_id("evt")
    cur.execute("""
    INSERT INTO conversation_memory (event_id, tenant_id, user_id, thread_id, run_id,
                                     turn_index, event_type, role, payload, created_at)
    VALUES (:e, :t, :u, 'thread_demo', 'run_demo', 2, 'model_msg', 'assistant',
            JSON('{ "text": "Correction: Helios-RAG BEIR score revised to 0.78." }'), TIMESTAMP '2026-08-17 00:00:00')
    """, e=corr_ev, t=TENANT_ACME, u=USER_ID)

    ent_v2 = new_id("ent")
    content_v2 = "Helios-RAG achieves 0.78 nDCG@10 on the BEIR benchmark (corrected)."
    cur.execute("""
    INSERT INTO entity_memory (
      id, tenant_id, user_id, agent_id, thread_id, subject, predicate, content, content_hash,
      content_json, embedding, confidence, written_by, source_event_id, version, valid_from, created_at
    )
    SELECT :new_id, tenant_id, user_id, agent_id, thread_id, subject, predicate,
           :c, :h, content_json,
           VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :c2 AS DATA),
           confidence, written_by, :ev, version + 1, TIMESTAMP '2026-08-17 00:00:00', TIMESTAMP '2026-08-17 00:00:00'
    FROM   entity_memory WHERE id = :old_id
    """, new_id=ent_v2, c=content_v2, h=sha256(content_v2), c2=content_v2, ev=corr_ev, old_id=ent_v1)

    cur.execute("""
    UPDATE entity_memory SET valid_until = TIMESTAMP '2026-08-17 00:00:00', superseded_by = :new_id
     WHERE id = :old_id AND valid_until IS NULL
    """, new_id=ent_v2, old_id=ent_v1)
    conn.commit()

    cur.execute("""
    SELECT version, SUBSTR(content,1,54) AS content, valid_until
      FROM entity_memory
     WHERE subject = 'model:helios-rag' AND predicate = 'beir_ndcg10'
     ORDER BY version
    """)
    print("Supersession chain (content + inline embedding moved together):")
    for r in cur:
        print(f"  v{r[0]}  {r[1]!r}  {'<active>' if r[2] is None else 'retired'}")
    sum_id = new_id("sum")
    summary = ("Evaluated Helios-RAG for the customer's retrieval stack. On BEIR it lands at "
               "0.78 nDCG@10 after the contamination correction, below the 0.85 bar the customer "
               "set, so we recommended against adopting it for the compliance corpus.")
    cur.execute("""
    INSERT INTO summarization_memory (
      id, tenant_id, user_id, task_type, title, summary, outcome,
      embedding, confidence, written_by, source_event_id, version, valid_from, completed_at, created_at
    ) VALUES (
      :id, :t, :u, 'model_eval', 'Helios-RAG evaluation for compliance corpus', :s, 'recommend_against',
      VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :s2 AS DATA),
      0.9, 'agent:research_v1', :ev, 1, TIMESTAMP '2026-08-18 00:00:00', TIMESTAMP '2026-08-18 00:00:00', TIMESTAMP '2026-08-18 00:00:00'
    )
    """, id=sum_id, t=TENANT_ACME, u=USER_ID, s=summary, s2=summary, ev=corr_ev)
    conn.commit()

    cur.execute("""
    SELECT title, outcome, CASE WHEN embedding IS NULL THEN 'no' ELSE 'yes' END
      FROM summarization_memory WHERE id = :id
    """, id=sum_id)
    r = cur.fetchone()
    print(f"Summary inserted inline: {r[0]!r}  outcome={r[1]!r}  embedding present: {r[2]}")
    # Stand-in for the document's fetched text (in production, read from source_uri).
    doc_text = (
      "Helios-RAG is a retrieval-augmented model for open-domain question answering. "
      "The original paper reported 0.92 nDCG@10 on the BEIR benchmark, averaged across its 14 "
      "retrieval tasks. A later erratum traced that figure to a data-contamination bug: several "
      "BEIR test passages had leaked into the training corpus, inflating retrieval scores. After "
      "removing the leaked passages and re-running the evaluation, the corrected score is 0.78 "
      "nDCG@10. The authors attribute the gap primarily to the MS MARCO and HotpotQA splits, "
      "where contamination was heaviest. The architecture and training recipe are unchanged; "
      "only the benchmark number was revised."
    )

    # Chunk-and-embed pipeline: chunk the source, embed each chunk, land in knowledge_base_chunk.
    INGEST_CHUNKS = """
    INSERT INTO knowledge_base_chunk (id, tenant_id, document_id, chunk_index, content, embedding, created_at)
    WITH chunks AS (
      SELECT JSON_VALUE(ct.column_value, '$.chunk_data')                AS chunk_data,
             JSON_VALUE(ct.column_value, '$.chunk_id' RETURNING NUMBER) AS chunk_id
      FROM   TABLE(DBMS_VECTOR_CHAIN.UTL_TO_CHUNKS(:doc_text, JSON(:params))) ct
    )
    SELECT 'kbc_' || LOWER(RAWTOHEX(SYS_GUID())),        -- unique id per chunk
           :tenant_id, :doc_id,
           ROW_NUMBER() OVER (ORDER BY chunk_id),        -- chunk_index 1..N
           chunk_data,
           VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING chunk_data AS DATA),
           TIMESTAMP '2026-08-18 00:00:00'
    FROM chunks
    """
    cur.execute(INGEST_CHUNKS, doc_text=doc_text,
                params='{"by":"words","max":80,"overlap":10}', tenant_id=TENANT_ACME, doc_id=kb_doc_id)
    conn.commit()

    cur.execute("""
    SELECT chunk_index, SUBSTR(content,1,58) FROM knowledge_base_chunk
     WHERE document_id = :d ORDER BY chunk_index
    """, d=kb_doc_id)
    rows = cur.fetchall()
    print(f"Ingested {len(rows)} chunks (each with an inline embedding):")
    for r in rows:
        print(f"  [{r[0]}] {r[1]!r}")


def seed_infrastructure(conn,cur):
    cur.execute("select count(*) from entity_memory where id=:id",id="ctxseed_4fb93df06968cd85a1f06dfb")
    if cur.fetchone()[0]:return
    counter=0
    def new_id(prefix):
        nonlocal counter
        counter+=1
        return "ctxseed_"+hashlib.sha256(f"seed_infrastructure:{prefix}:{counter}".encode()).hexdigest()[:24]
    def insert_conv_event(event_id,turn_index,event_type,role,payload):
        cur.execute("INSERT INTO conversation_memory(event_id,tenant_id,user_id,thread_id,run_id,turn_index,event_type,role,payload,created_at) VALUES(:id,:t,:u,'thread_demo','run_demo',:ix,:typ,:role,JSON(:p),TIMESTAMP '2026-07-02 00:00:00')",id=event_id,t=TENANT_ACME,u=USER_ID,ix=turn_index,typ=event_type,role=role,p=payload)
    new_event = new_id("evt")
    # Source event (simulating a model deciding a new fact)
    insert_conv_event(new_event, 3, "model_msg", "assistant",
                      '{ "text": "Acme production DB moved us-east-1 -> eu-west-1." }')

    new_entity_id = new_id("ent")
    content_v1 = "Production database is in us-east-1, replicas in us-west-2."
    cur.execute("""
    INSERT INTO entity_memory (
      id, tenant_id, user_id, agent_id, thread_id,
      subject, predicate, content, content_hash, embedding,
      confidence, written_by, source_event_id, version,
      valid_from, created_at
    ) VALUES (
      :id, :tenant_id, :user_id, NULL, NULL,
      'customer:acme-corp', 'infrastructure',
      :content,
      :content_hash,
      VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :content AS DATA),
      0.95, 'agent:support_asst', :source_event_id, 1,
      TIMESTAMP '2026-07-03 00:00:00', TIMESTAMP '2026-07-03 00:00:00'
    )
    """, id=new_entity_id, tenant_id=TENANT_ACME, user_id=USER_ID,
         content=content_v1, content_hash=sha256(content_v1),
         source_event_id=new_event)

    conn.commit()
    print(f"Inserted entity {new_entity_id} (version 1).")
    new_event_v2 = new_id("evt")
    insert_conv_event(new_event_v2, 4, "model_msg", "assistant",
                      '{ "text": "Migration confirmed." }')

    new_v2_id = new_id("ent")
    content_v2 = "Production database is in eu-west-1, replicas in eu-central-1. Migrated 2026-04."

    cur.execute("""
    DECLARE
      v_now TIMESTAMP := TIMESTAMP '2026-07-03 00:00:00';
    BEGIN
      INSERT INTO entity_memory (
        id, tenant_id, user_id, agent_id, thread_id,
        subject, predicate, content, content_hash, embedding, confidence,
        written_by, source_event_id, version, valid_from, created_at
      ) VALUES (
        :new_id, :tenant_id, :user_id, NULL, NULL,
        'customer:acme-corp', 'infrastructure',
        :content,
        :content_hash_v2,
        VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :content AS DATA),
        0.97,
        'agent:support_asst', :new_event, 2, v_now, v_now
      );

      UPDATE entity_memory
         SET valid_until = v_now, superseded_by = :new_id
       WHERE id = :old_id AND valid_until IS NULL;
    END;
    """, new_id=new_v2_id, tenant_id=TENANT_ACME, user_id=USER_ID,
         content=content_v2, content_hash_v2=sha256(content_v2),
         new_event=new_event_v2, old_id=new_entity_id)
    conn.commit()

    # Verify the supersession chain.
    cur.execute("""
    SELECT id, version, content, valid_until, superseded_by
      FROM entity_memory
     WHERE subject = 'customer:acme-corp' AND predicate = 'infrastructure'
     ORDER BY version
    """)
    print("Supersession chain:")
    for r in cur:
        iv = r[3].isoformat() if r[3] else "<active>"
        print(f"  v{r[1]} id={r[0]}  valid_until={iv}  superseded_by={r[4]}")
