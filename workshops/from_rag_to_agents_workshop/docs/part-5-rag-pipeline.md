# Part 5: Building a RAG Pipeline [Generation Layer]

## What You Are Building

In Parts 2-4 you built the retrieval layer. Now you connect it to generation — completing the Retrieval-Augmented Generation pipeline end to end:

1. Configure OpenAI API access
2. Initialise and smoke-test the client
3. Build a reusable RAG function that supports all retrieval modes
4. Run an end-to-end query

The result is a single function that takes a user question, retrieves relevant papers from Oracle, and generates a grounded, cited answer using OpenAI.

## Configure API Access

The notebook reads `OPENAI_API_KEY` from environment variables. In GitHub Codespaces, set it as a Codespace secret so it is available automatically. For local development, export it in your shell before launching Jupyter.

## Initialise the OpenAI Client

A simple smoke test confirms credentials work:

```python
from openai import OpenAI
openai_client = OpenAI(api_key=openai_api_key)
response = openai_client.responses.create(
    model="gpt-5",
    input="Hello!",
    instructions="You are a research paper assistant.",
)
```

---

## TODO 4: Implement `research_paper_assistant_rag_pipeline`

This is the core RAG function. It connects retrieval (Part 4) to generation (OpenAI) in a single callable pipeline.

**Requirements:**

1. **Select retrieval strategy** based on `retrieval_mode` parameter (keyword, vector, hybrid, graph)
2. **Call the appropriate retrieval function** from Part 4
3. **Format retrieved rows** into citation-ready context with titles, abstracts, and scores
4. **Construct a prompt** that includes the user query and formatted context
5. **Call the OpenAI Responses API** with grounding instructions
6. **Return** the generated text

**Why route by mode?** Different queries benefit from different retrieval strategies. A single function that accepts a `retrieval_mode` parameter lets the caller (or a future agent) choose the best strategy per query without duplicating the generation logic.

**Why numbered citations?** Citations like `[1]`, `[2]` create a verifiable chain from the generated answer back to specific papers. Without them, the user cannot distinguish grounded claims from hallucination.

**Complete solution:**

```python
def research_paper_assistant_rag_pipeline(
    conn, embedding_model, user_query, top_k=10,
    retrieval_mode="hybrid", show_explain=False
):
    # 1. Retrieve
    if retrieval_mode == "keyword":
        rows, columns = keyword_search_research_papers(conn, user_query)
    elif retrieval_mode == "vector":
        rows, columns = vector_search_research_papers(conn, embedding_model, user_query, top_k)
    elif retrieval_mode == "graph":
        rows, columns = graph_search_research_papers(conn, embedding_model, user_query, top_k=top_k)
    else:
        rows, columns, _ = hybrid_search_research_papers_pre_filter(
            conn=conn, embedding_model=embedding_model,
            search_phrase=user_query, top_k=top_k, show_explain=show_explain
        )

    # 2. Format context
    retrieved_count = len(rows) if rows else 0
    formatted_context = ""
    if retrieved_count > 0:
        for i, row in enumerate(rows):
            row_data = dict(zip(columns, row))
            title = row_data.get("TITLE", "Untitled")
            abstract = row_data.get("ABSTRACT", "No abstract.")
            score = (row_data.get("GRAPH_SCORE") or row_data.get("SIMILARITY_SCORE")
                     or row_data.get("RELEVANCE_SCORE") or "N/A")
            formatted_context += f"[{i+1}] {title}\nAbstract: {abstract}\nScore: {score}\n\n"

    # 3. Call LLM
    prompt = f"""User Query: {user_query}
    Retrieved papers: {retrieved_count}
    {formatted_context}
    Summarize findings. Use [X] citations. Highlight consensus and gaps."""

    response = openai_client.responses.create(
        model=OPENAI_MODEL, input=prompt,
        instructions="You are a scientific research assistant. Use only provided context. Cite papers [1], [2], etc.",
    )
    return response.output_text
```

**What `instructions` vs `input` does:** The `instructions` field is the system-level directive (how to behave). The `input` field is the user-level content (what to answer). Separating them gives the model clear role boundaries.

## Troubleshooting

**"Invalid API key"** — Verify your `OPENAI_API_KEY` environment variable is set correctly.

**Empty retrieval** — Check Part 4 functions work independently before debugging the pipeline. Run a vector search directly and verify it returns results.

**Low-quality answers** — Check that `formatted_context` is not empty. If retrieval returns results but the context is blank, the `dict(zip(columns, row))` mapping may have a column name mismatch — print `columns` to debug.
