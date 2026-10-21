corrections = [
    "Remember: transactions.amount_cents is USD CENTS, never dollars.",
    "Also: customers.risk_rating is a 1-100 score, higher means riskier.",
    "Third: branches.region is one of AMERICAS, EUROPE, MIDDLE_EAST, ASIA_PACIFIC.",
    "Fourth: SAR_REPORTS is compliance-only and forbidden to analysts.",
]
raw, card = store.raw_vs_card("context-demo", corrections)
print(f"raw transcript: {len(raw)} chars in {len(corrections)} messages")
print(f"context card:   {len(card)} chars, raw : card = {len(raw) / max(len(card), 1):.2f}")
print("card preview:", card[:280].replace("\n", " "))
