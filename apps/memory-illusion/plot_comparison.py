"""Draw the money shot: flat history vs Agent Memory, tokens per request.

Run AFTER both demos:  ./.venv/bin/python plot_comparison.py
Produces token_comparison.png (your own local reproduction of the paper's Fig. 5).
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

flat = json.load(open("flat_log.json"))
mem = json.load(open("memory_log.json"))
turns = range(1, len(flat) + 1)

fig, ax = plt.subplots(figsize=(11, 6), dpi=150)
ax.plot(
    turns,
    flat,
    color="#c74634",
    lw=3,
    marker="o",
    ms=5,
    label="Flat history — full transcript re-sent every turn",
)
ax.plot(
    turns,
    mem,
    color="#12805c",
    lw=3,
    marker="o",
    ms=5,
    label="Oracle Agent Memory — context card + question",
)

ax.annotate(
    f"{flat[-1]:,} tokens",
    (len(flat), flat[-1]),
    xytext=(-10, 12),
    textcoords="offset points",
    ha="right",
    fontsize=12,
    fontweight="bold",
    color="#c74634",
)
ax.annotate(
    f"{mem[-1]:,} tokens",
    (len(mem), mem[-1]),
    xytext=(-10, 14),
    textcoords="offset points",
    ha="right",
    fontsize=12,
    fontweight="bold",
    color="#12805c",
)

ratio = flat[-1] / max(1, mem[-1])
ax.set_title(
    f"Input tokens per request — same scripted conversation\n"
    f"final turn: {ratio:.1f}× more tokens without a memory layer",
    fontsize=14,
    fontweight="bold",
    pad=14,
)
ax.set_xlabel("conversation turn")
ax.set_ylabel("estimated input tokens (chars ÷ 4)")
ax.legend(frameon=False, fontsize=11)
ax.grid(alpha=0.25)
ax.spines[["top", "right"]].set_visible(False)

fig.tight_layout()
fig.savefig("token_comparison.png")
print(
    f"saved token_comparison.png  ·  final-turn ratio: {ratio:.1f}×  "
    f"(total {sum(flat):,} vs {sum(mem):,})"
)
