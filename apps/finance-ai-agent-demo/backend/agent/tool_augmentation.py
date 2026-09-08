"""Tool augmentation: LLM-enhanced descriptions + synthetic activation queries.

Follows the pattern from notebooks/memory_context_engineering_agents.ipynb (Cell 62).
Tools are augmented once at startup and stored in TOOLBOX_MEMORY for hybrid retrieval.
"""

import json

from config import OPENAI_MODEL


def augment_description(llm_client, tool_schema):
    """Use LLM to improve a tool's description for better searchability.

    Takes the raw tool schema and returns an enhanced description that is
    clearer, more comprehensive, and more discoverable via semantic search.
    """
    func = tool_schema["function"]
    name = func["name"]
    description = func.get("description", "")
    params = json.dumps(func.get("parameters", {}), indent=2)

    prompt = f"""You are a technical writer. Improve the following tool description to be more clear,
comprehensive, and useful for semantic search. Include:
1. A clear concise summary of what the tool does
2. When to use this tool (specific scenarios)
3. What data it returns
4. Any important constraints or prerequisites

Tool name: {name}
Original description: {description}
Parameters: {params}

Return ONLY the improved description text, no other text or formatting."""

    response = llm_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=400,
    )
    return response.choices[0].message.content.strip()


def generate_activation_queries(llm_client, tool_schema, augmented_desc, n=5):
    """Generate synthetic queries that would lead to using this tool.

    These queries improve retrieval — by embedding both the tool description
    AND example queries, we increase the chances of finding the right tool
    when a user asks a related question.
    """
    name = tool_schema["function"]["name"]

    prompt = f"""Based on the following tool, generate {n} diverse example queries that a financial
services employee might ask when they need this tool. Make them natural, varied, and realistic.

Tool name: {name}
Description: {augmented_desc}

Return ONLY a JSON array of strings, like: ["query1", "query2", ...]"""

    response = llm_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=300,
    )

    try:
        raw = response.choices[0].message.content.strip()
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            return [raw]
        queries = json.loads(raw[start : end + 1])
        return queries if isinstance(queries, list) else [raw]
    except (json.JSONDecodeError, ValueError):
        return [response.choices[0].message.content.strip()]


def build_embedding_text(tool_schema, augmented_desc, queries):
    """Build rich text for embedding and full-text search.

    Concatenates name + augmented description + parameter schema + activation queries.
    This text is stored as the searchable `text` column in TOOLBOX_MEMORY and
    also used to generate the vector embedding.
    """
    func = tool_schema["function"]
    name = func["name"]
    params_str = json.dumps(func.get("parameters", {}))
    queries_str = " ".join(queries) if queries else ""

    return f"{name} {augmented_desc} {params_str} {queries_str}"


def seed_toolbox(memory_manager, llm_client, tool_schemas, force=False):
    """Augment all tool schemas and store them in TOOLBOX_MEMORY.

    Performs LLM-powered augmentation (improved descriptions + activation queries)
    and seeds the toolbox vector store. Skips if tools already exist unless force=True.
    """
    # Check if already seeded
    if not force:
        try:
            existing = memory_manager.toolbox_vs.similarity_search("tool", k=1)
            if existing:
                count = len(memory_manager.toolbox_vs.similarity_search("tool", k=50))
                print(f"  Toolbox already seeded ({count} tools), skipping.")
                return
        except Exception:
            pass  # Empty table, proceed with seeding

    print(f"  Augmenting and seeding {len(tool_schemas)} tools...")

    for i, schema in enumerate(tool_schemas):
        name = schema["function"]["name"]
        print(f"  [{i + 1}/{len(tool_schemas)}] {name}...", end=" ", flush=True)

        try:
            # Step 1: Augment the description
            augmented_desc = augment_description(llm_client, schema)

            # Step 2: Generate activation queries
            queries = generate_activation_queries(llm_client, schema, augmented_desc)

            # Step 3: Build rich embedding text
            embedding_text = build_embedding_text(schema, augmented_desc, queries)

            # Step 4: Build metadata (OpenAI-compatible schema + augmentation data)
            metadata = {
                "name": name,
                "description": augmented_desc,
                "parameters": schema["function"].get(
                    "parameters", {"type": "object", "properties": {}}
                ),
                "queries": queries,
                "augmented": True,
                "original_description": schema["function"].get("description", ""),
            }

            # Step 5: Store in TOOLBOX_MEMORY
            memory_manager.write_toolbox(embedding_text, metadata)
            print(f"done ({len(queries)} queries)")

        except Exception as e:
            print(f"FAILED: {e}")
            # Fall back: store with original description, no augmentation
            try:
                func = schema["function"]
                fallback_text = (
                    f"{name} {func.get('description', '')} {json.dumps(func.get('parameters', {}))}"
                )
                metadata = {
                    "name": name,
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {"type": "object", "properties": {}}),
                    "queries": [],
                    "augmented": False,
                }
                memory_manager.write_toolbox(fallback_text, metadata)
                print("  (stored with original description as fallback)")
            except Exception as e2:
                print(f"  Fallback also failed: {e2}")

    print("  Toolbox seeding complete.")
