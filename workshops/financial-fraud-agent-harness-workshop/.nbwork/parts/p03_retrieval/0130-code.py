# Try it: an exact column name. Keyword search finds RATE_BP by its name, so it ends up first.
for h in hybrid_search_knowledge("which column holds RATE_BP", k=3):
    print(f"{h['rrf_score']:.4f}  vector #{h['vec_rank']}  keyword #{h['txt_rank']}  {h['subject']}")
