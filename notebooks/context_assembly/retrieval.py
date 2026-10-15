"""Query understanding and RRF/BGE retrieval from Hybrid Retrieval."""
import re
CONCEPT_CLUSTERS = [
    {"eviction", "evict", "expiry", "expire", "retention", "pruning", "prune",
     "forgetting", "compaction", "truncation", "flush"},
    {"summarization", "summary", "summarize", "compression", "distillation", "rollup"},
    {"context window", "working set", "working context", "main context", "buffer"},
    {"long-term memory", "archival memory", "durable memory", "persistent memory"},
    {"short-term memory", "session memory", "recall memory", "event stream"},
    {"retrieval", "search", "recall", "lookup"},
]

_STOP_CAPS = {"what", "how", "the", "did", "and", "does", "that", "compare", "to", "a",
              "an", "when", "which", "where", "why", "is", "do", "can", "i", "in", "if",
              "should", "are", "was", "were", "will", "would", "could", "no", "not"}

_STOP_WORDS = _STOP_CAPS | {"of", "for", "on", "at", "by", "with", "from", "it", "its",
                            "be", "as", "or", "but", "so", "than", "then", "this", "these",
                            "there", "their", "you", "your", "we", "our", "they", "them",
                            "does", "did", "done", "use", "used", "using", "need", "needs",
                            "make", "makes", "get", "gets", "one", "any", "all", "some",
                            "ever", "much", "many", "most", "more", "less", "between"}

_PHRASES = sorted({t for c in CONCEPT_CLUSTERS for t in c if " " in t}, key=len, reverse=True)

def understand_query(question: str, *, collections=None, token_budget=2000) -> dict:
    """Decompose a question into the plan that parameterizes stages 2-6.

    Production swaps this for a single fast-model call returning the same JSON shape.
    """
    lowered = question.lower()

    # Entities: capitalized tokens that are not sentence-initial filler. Crude on purpose --
    # a model does this better, and the plan shape is what matters downstream.
    entities = []
    for tok in re.findall(r"\b[A-Z][A-Za-z0-9]+\b", question):
        if tok.lower() not in _STOP_CAPS and tok not in entities:
            entities.append(tok)

    # Concept expansion: for every cluster the question touches, take the whole cluster.
    matched, expanded = [], set()
    for phrase in _PHRASES:
        if phrase in lowered:
            matched.append(phrase)
    for cluster in CONCEPT_CLUSTERS:
        hit = any(p in lowered for p in cluster if " " in p) or any(
            re.search(rf"\b{re.escape(t)}\b", lowered) for t in cluster if " " not in t
        )
        if hit:
            expanded |= cluster

    # Intent: comparisons need budget reserved per source; lookups do not.
    if re.search(r"\bcompare\b|\bversus\b|\bvs\.?\b|difference between|how does that", lowered):
        intent = "comparison"
    elif re.search(r"\bhow (do|did) (we|i|you)\b|last time|previously", lowered):
        intent = "procedural_recall"
    else:
        intent = "factual_lookup"

    return {
        "question": question,
        "entities": entities,
        "expanded_terms": sorted(expanded),
        "intent": intent,
        "collections": collections or ["ingested-papers", "vendor-docs"],
        "token_budget": token_budget,
        "diversify_by": "document_id" if intent == "comparison" else None,
    }

def build_lexical_query(plan: dict) -> str:
    """Render the plan as an Oracle Text expression.

    Every term is wrapped in {} so Oracle Text treats it as a literal. This is not
    cosmetic: Oracle Text reserves ABOUT, ACCUM, AND, NEAR, NOT, MINUS, WITHIN and others
    as operators, so an ordinary English word like "within" is a syntax error unescaped
    (DRG-50901). Braces also neutralise hyphens and other punctuation.
    """
    def lit(t):
        return "{" + t.replace("{", "").replace("}", "") + "}"

    terms = [lit(e) for e in plan["entities"]]
    for t in plan["expanded_terms"]:
        terms.append(lit(t))

    # Fallback: a question with no proper nouns and no thesaurus hit would otherwise
    # produce an empty CONTAINS expression, which is a parser error rather than an empty
    # result. Fall back to the question's own content words.
    if not terms:
        words = [w for w in re.findall(r"[A-Za-z0-9]+", plan["question"].lower())
                 if w not in _STOP_WORDS and len(w) > 2]
        terms = [lit(w) for w in dict.fromkeys(words)] or [lit("memory")]

    return " OR ".join(terms)
