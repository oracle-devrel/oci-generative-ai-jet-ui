# Part 7 — Naive substring vs semantic vector search

## The problem with keyword search on real catalogues

Pretend you're a merchandising planner. You walk into the office and
ask the assistant: _"How are our soccer-related items moving?"_

If the assistant uses keyword search, it scans every catalogue row for
the word **"soccer"** and returns matches. That works fine — _if_ the
catalogue uses the word "soccer." Real catalogues don't:

- Brand language: _adidas Brazuca 2017 Official Match Ball_
- Sport-of-origin language: _FIFA_
- Generic-equipment language: _Match Ball_, _Cleat_
- Misclassification: a football cleat filed under _baseball & softball_
  because someone fat-fingered the category dropdown

None of those rows contain the literal word _soccer_. A keyword filter
returns **zero matches**, and the planner walks away thinking we don't
sell anything soccer-related.

## The fix: vector search

Vector search doesn't care which words the document used. It embeds
both the query and the documents into the same 384-dim space, then
ranks by cosine similarity. _"soccer merchandise demand"_ lives near
_Adidas RG III Mid Football Cleat_ in that space because
sentence-transformer training has taught the model that **soccer**,
**football**, **cleat**, **FIFA**, and **match ball** all relate.

This is the entire reason we wired in an embedder. Without it the
agent could only retrieve documents that already use the planner's
vocabulary.

## What you'll build in TODO 6

A side-by-side comparison:

| Side         | Implementation                                                  | Expected hits                              |
| ------------ | --------------------------------------------------------------- | ------------------------------------------ |
| **Naive**    | Fetch every demand report and `re.search` for `\bsoccer\b`      | **0**                                      |
| **Semantic** | `oracle_vs.similarity_search("soccer merchandise demand", k=5)` | **≥ 3** (kids' cleats, men's cleats, etc.) |

The hard-stop checkpoint asserts naive = 0 and semantic ≥ 3. If the
naive side ever finds a match, the seed step is generating text that
contains the literal word "soccer" — re-check
`app/scripts/seed_supplychain.py` (it doesn't).

## Solution

Drop this into the TODO 6 cell, replacing the `naive = []` / `hits = []`
placeholders:

```python
import re

# Naive substring filter — fetch all demand_report rows and grep them.
all_hits = oracle_vs.similarity_search("demand report", k=50)
all_reports = [h for h in all_hits if (h.metadata or {}).get("type") == "demand_report"]
naive = [
    (h.metadata or {}).get("product")
    for h in all_reports
    if re.search(r"\bsoccer\b", h.page_content, re.IGNORECASE)
]
print(f"NAIVE substring 'soccer' → {len(naive)} hits: {naive}")

# Semantic vector search via OracleVS.
hits = oracle_vs.similarity_search("soccer merchandise demand", k=5)
print(f"\nSEMANTIC 'soccer merchandise demand' → {len(hits)} hits:")
for d in hits:
    print(f"  {d.page_content.splitlines()[0]}")
```

## What the semantic side returns

A typical result on `gpt-5.5`:

```
SEMANTIC 'soccer merchandise demand' → 5 hits:
  Demand intelligence — adidas Kids' RG III Mid Football Cleat
  Demand intelligence — Nike Men's CJ Elite 2 TD Football Cleat
  Demand intelligence — Nike Men's Dri-FIT Victory Golf Polo
  Demand intelligence — Nike Men's Comfort 2 Slide
  Demand intelligence — Columbia Men's PFG Anchor Tough T-Shirt
```

The top two — both football cleats — are exactly what the planner
wants. The bottom three are weaker matches that the embedder thinks
might still be sport-adjacent. That's fine: the `demand_analyst` agent
will filter further when it answers.

## Takeaway

Vector search lets users **ask in their own words** rather than
memorising the catalogue's vocabulary. For merchandising, support
ticketing, internal documentation, knowledge bases — anywhere humans
describe things differently than the system stores them — this is the
right primitive.

## Next

→ **[Part 8 — `demand_analyst` specialist](part-8-demand-analyst.md)** — the first agent, and the one that uses semantic search directly.
