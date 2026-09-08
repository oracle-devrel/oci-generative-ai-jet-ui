"""Pattern 2 benchmark: measure token cost of payload-by-reference.

Compares two ways to express the same Researcher-to-Writer task in A2A:
  1. Naive: findings serialized into the message payload
  2. Payload-by-reference: only a memory_id, Writer reads findings from Oracle

Counts tokens using tiktoken (OpenAI's cl100k_base, GPT-4 family).
This is a reasonable proxy for Anthropic and Google tokenizers; they
typically produce token counts within +/- 15% of each other for English text.

Usage:
    pip install tiktoken
    python pattern2/measure_tokens.py
"""
import json
import random
import statistics

import tiktoken

random.seed(42)

# Use cl100k_base (GPT-4 family). For Claude or Gemini, swap the encoding.
# The relative reduction will be similar regardless of tokenizer.
ENCODER_NAME = "cl100k_base"
enc = tiktoken.get_encoding(ENCODER_NAME)


def count_tokens(message: dict) -> int:
    """Count tokens in a serialized A2A message envelope."""
    serialized = json.dumps(message, separators=(",", ":"))
    return len(enc.encode(serialized))


def synthetic_findings(target_chars: int = 3000) -> str:
    """Generate realistic research findings of approximately target_chars length.

    The naive payload is dominated by findings text and source references,
    which is exactly what the payload-by-reference pattern eliminates.
    """
    sentences = [
        "The team's experiments show that vector indexing reduces query latency by roughly an order of magnitude for corpora above 10,000 entries.",
        "Cross-referencing the Anthropic MCP specification reveals that capability cards function as a typed contract between model and server, discoverable at connection time.",
        "Empirical data from production deployments at three Fortune 500 firms suggest a consistent pattern of declining marginal returns once protocol surface area exceeds three layers.",
        "The 2024 Google A2A protocol paper documents task lifecycle states (submitted, working, completed, failed) and their associated retry semantics.",
        "Microservice architects who introduced agent meshes without corresponding observability investments reported a 60 percent increase in mean time to diagnosis.",
        "Findings from a longitudinal study of 47 enterprise agent deployments indicate that durable memory layers significantly outperform ephemeral payload-passing approaches.",
        "The MCP discovery layer transforms tool selection from a routing problem into a reasoning problem, with measurable effects on graceful failure handling.",
        "Researchers note that payload-by-reference patterns become economically critical at the third hop in any multi-agent mesh, where token costs begin to compound exponentially.",
    ]
    text = ""
    while len(text) < target_chars:
        text += random.choice(sentences) + " "
    return text[:target_chars]


def synthetic_source_refs(n: int = 12) -> list[dict]:
    """Generate realistic source reference objects."""
    return [
        {
            "id": f"src_{i:04d}",
            "title": f"Paper or document title {i} on agent architectures",
            "url": f"https://example.com/research/agent-paper-{i}",
            "excerpt": "Relevant excerpt of roughly 200 characters drawn from the source material, included to support claims made in the findings section above. "
            * 1,
            "confidence": round(random.uniform(0.5, 0.95), 2),
        }
        for i in range(n)
    ]


def build_naive_message(findings: str, source_refs: list[dict]) -> dict:
    """The payload-in-message version. Findings and sources travel inline."""
    return {
        "task_id": "task_001",
        "from_agent": "researcher-v1",
        "to_agent": "writer-v1",
        "intent": "draft_response",
        "status": "submitted",
        "payload": {
            "tone": "technical",
            "target_length_words": 800,
            "findings": findings,
            "source_refs": source_refs,
        },
    }


def build_reference_message(memory_id: str) -> dict:
    """The payload-by-reference version. Findings live in Oracle; message carries an ID."""
    return {
        "task_id": "task_001",
        "from_agent": "researcher-v1",
        "to_agent": "writer-v1",
        "intent": "draft_response",
        "status": "submitted",
        "payload": {
            "tone": "technical",
            "target_length_words": 800,
            "memory_id": memory_id,
        },
    }


def main() -> None:
    print(f"Tokenizer: {ENCODER_NAME}")
    print("=" * 60)

    # Single representative measurement
    findings = synthetic_findings(target_chars=3000)
    source_refs = synthetic_source_refs(n=12)

    naive_msg = build_naive_message(findings, source_refs)
    ref_msg = build_reference_message(memory_id="mem_a1b2c3d4e5f6")

    naive_tokens = count_tokens(naive_msg)
    ref_tokens = count_tokens(ref_msg)
    reduction = naive_tokens / ref_tokens

    print("\nSingle-message comparison:")
    print(f"  Naive (payload in message):    {naive_tokens:>6,} tokens")
    print(f"  Payload-by-reference:          {ref_tokens:>6,} tokens")
    print(f"  Reduction:                     {reduction:>6.1f}x")

    # Vary findings size to show the relationship holds across realistic sizes
    print("\nReduction across findings sizes:")
    print(f"  {'Findings size':<18} {'Naive':>10} {'By-ref':>10} {'Reduction':>12}")
    print(f"  {'-' * 16}   {'-' * 8}   {'-' * 8}   {'-' * 10}")

    reductions = []
    for size in [500, 1000, 2000, 3000, 5000, 8000]:
        f = synthetic_findings(target_chars=size)
        # Scale source refs roughly with findings size
        s = synthetic_source_refs(n=max(3, size // 250))
        n_msg = build_naive_message(f, s)
        r_msg = build_reference_message(memory_id="mem_a1b2c3d4e5f6")
        n_tok = count_tokens(n_msg)
        r_tok = count_tokens(r_msg)
        red = n_tok / r_tok
        reductions.append(red)
        print(f"  {size:>5} chars       {n_tok:>10,}   {r_tok:>8,}   {red:>10.1f}x")

    print(f"\n  Median reduction across sizes:  {statistics.median(reductions):>6.1f}x")
    print(
        f"  Range:                          {min(reductions):.1f}x to {max(reductions):.1f}x"
    )

    # Compounding across hops
    print("\nCompounding across mesh hops:")
    print("  (Each hop forwards the same payload to the next agent)")
    print(
        f"  {'Hops':<8} {'Naive cumulative':>20} {'By-ref cumulative':>20} {'Compounded gap':>18}"
    )
    print(f"  {'-' * 6}   {'-' * 18}   {'-' * 18}   {'-' * 16}")

    for hops in [1, 2, 3, 5]:
        n_cum = naive_tokens * hops
        r_cum = ref_tokens * hops
        gap = n_cum - r_cum
        print(f"  {hops:>4}     {n_cum:>18,}   {r_cum:>18,}   {gap:>16,}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
