# Demo

In the Java backend logs you will see:

- `[EPISODIC]`
- `[SEMANTIC]`
- `[PROCEDURAL]`

Inthe case of the semantic memory, you will see the payload for the Oracle AI Database 26ai for Hybrid Vector Index:

```text
[SEMANTIC] Hybrid search JSON: {
  "hybrid_index_name": "POLICY_HYBRID_IDX",
  "search_scorer": "rrf",
  "search_fusion": "UNION",
  "vector": {
    "search_text": "What is my name?"
  },
  "text": {
    "contains": "What OR name"
  },
  "return": {
    "values": ["chunk_text", "score", "vector_score", "text_score"],
    "topN": 5
  }
}
```

## Example of chat

```text
Hello, my name is Victor.
```

```text
I want to know what is the return policy.
```

```text
show me my orders
```

```text
From now on, I want the answers in Spanish. What are the details of ORD-1008?
```

```text
I want to return ORD-1008 because the mouse is not ergonomic enough.
```

```text
Please, return ORD-1008
```

```text
What is my name?
```
