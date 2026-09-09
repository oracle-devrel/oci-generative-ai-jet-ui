# Loop engineering: keeping the loops honest

Once your second brain is fully set up, it runs itself: a daily sync pulls in new content,
the wiki recompiles around it, memory consolidates overnight, a heartbeat records that it
all happened. Each of those is a **loop** — a job that runs on a schedule, without you
watching. The whole point of the system is that you *don't* babysit it.

That's also the risk. Automation has one signature failure mode: it fails **quietly**.
A token expires and a source just stops loading — no error you'll see, the brain simply
gets staler. A scheduled job breaks (a folder gets renamed, a machine sleeps through its
window) and nothing announces it. An LLM step keeps spending money nobody is counting.
A "self-improving" pipeline that fails like this doesn't look broken — it looks fine,
for weeks, while it quietly isn't. Every one of those examples happened in this repo.

So the loops don't get to run on trust. Each one is built to stay **accountable** — to
prove it works, report what it costs, and make its failures loud. That discipline has a
name now — [**loop engineering**](https://addyosmani.com/blog/loop-engineering/) (Addy
Osmani's term, from the coding-agent world; Boris Cherny: "my job is writing loops") —
and this repo applies it to a knowledge system: you don't maintain the brain, you design
the loops that maintain it, and then you hold those loops to the rules below:

- **Every loop earns its keep.** A source, agent, or scheduled job ships with an eval proving
  it works or a report you actually read — otherwise it's a removal candidate, not furniture.
- **Loops report their spend.** Every LLM call lands in a local ledger tagged by loop
  (`exports/loop_ledger.jsonl`, written by `llm.py`; `LOOP_LABEL` names the loop, and the sync
  tags each step automatically). "Is this loop worth it?" gets a denominator.
- **Failures escalate instead of whispering.** The sync writes per-step outcomes to
  `exports/sync_status.json` locally AND as a **heartbeat row in the database**
  (`sync_runs`, via `oracle/agent/health.py`, as the sync's last act); anything failing
  or skipping repeatedly should headline your weekly review, not hide in a log. (A
  missing API token once silently skipped a source here for weeks — this exists so that
  can't happen quietly again.)
- **Downtime is visible from anywhere.** The machine that runs your sync will sometimes
  be off or asleep — and a system that can't say so just looks quietly stale. Because the
  heartbeat lives in the *database*, the hosted MCP's `source_status` panel can tell you
  from your phone: `LOCAL PIPELINE: DOWN — last sync run 49h ago` (machine-local
  capabilities unavailable until it wakes; hosted search/wiki still fine — the panel
  itself is proof). The rule underneath: measure **time since last SUCCESS**, never time
  since last attempt, and store that proof somewhere that outlives the machine that
  produced it.
- **Make the alarm push, not pull (optional watchdog).** A panel only helps if you look
  at it. The upgrade is a tiny scheduled check — any scheduler you already have (your AI
  app's scheduled tasks, cron/launchd, or a job on the host that runs your MCP server) —
  that calls `source_status` and notifies you on your messaging platform of choice ONLY
  when the pipeline is degraded or down. Two design rules: **silence means healthy**
  (a watchdog that messages daily gets muted, then ignored), and know your watchdog's
  blind spot — a checker running on the same machine as the sync can only alert
  *after* that machine wakes ("this broke while you were away"); a checker on always-on
  infrastructure catches it in real time. Start with the free same-machine version;
  graduate to the hosted one if the gap ever bites.
- **Every loop has a row in a registry.** One file lists every agent and scheduled job:
  its trigger, what it reads, what it writes, whether it touches an LLM or the network —
  plus the standing rules they all obey (scheduled jobs use APIs and local files only,
  never a logged-in browser; report-only by default — loops *propose*, the human
  applies). The registry is what you audit when something feels off, and the bar a new
  loop must clear before it exists: no row, no run.
- **Check the docs against reality.** Registries and system docs drift the moment
  someone adds a loop in a hurry and forgets to write it down. A mechanical drift check
  — registry vs. the agents directory, documented schedules vs. installed jobs,
  documented sources vs. what the sync actually configures — flags mismatches in a
  report you already read. Docs you don't verify are just wishes with formatting.
- **Rehearse the restore.** A backup you've never restored is a hypothesis. Periodically
  rebuild from scratch — fresh clone, schema, re-ingest from exports, point at the
  database — and let the drill tell you what monitoring can't: the credential that
  silently expired, the archive that exists on exactly one machine. The drill here found
  both, including the expired token behind the README's favorite cautionary tale.
- **New agents climb a permission ladder: Read → Remember → Propose → Act.** An agent starts
  read-only. It earns the right to *remember* (write memory) once you trust its results, and to
  *propose* changes (report-only output you apply by hand) before it may ever apply them. The
  top rung stays narrow: anything touching money, publishing, deletion, or another person is
  human-approved every time — some agents should simply never reach it.
- **Match the boundary to what the platform can enforce.** Three tiers, strongest first:
  *structural* where the platform offers it (a service account that can only see the
  folders you explicitly share — the rest of the drive is invisible by construction);
  *code-enforced* where it doesn't (a whole-mailbox read grant that your loader
  restricts to one opt-in label by convention); *human-present-only* where the data is
  personal (a break-glass CLI with credentials in the OS keychain — never scheduled,
  never hosted, every use consented). Standing automation belongs only behind the first
  two fences; personal scopes get hand tools, not infrastructure.
- **Forgetting is a designed stage.** A memory store that only grows drifts toward noise.
  `scripts/memory_review.py` is the report-only audit: stale time-bound facts, near-duplicate
  pairs, volume growth. Review it, retire by hand — deleting memories is the one loop that
  should never run unattended first.

The privacy filter is part of the loop, not an afterthought: consolidation and the wiki only read
`visibility = 'content'`, so a private item can never be laundered into a "learned" fact. Accuracy
is guarded the same way: a verification pass fact-checks every research answer against the run's
own evidence before it is returned or remembered, and consolidation refuses to promote unverified
claims into durable facts — so the loop compounds knowledge, not mistakes.

And because quality can regress silently, the repo ships **evals** alongside the tests (plain
Python + JSON golden sets, no framework): `tests/eval_retrieval.py` (golden queries that must keep
ranking — free, in-database), `eval_classifier.py` (privacy-classifier drift vs your reviewed
labels), `eval_verify.py` (a fabrication probe for the accuracy gate), `eval_grounding.py`
(do answers cite the sources they should?), and `eval_oamp.py` (seven probes for the memory
package — extraction smoke, privacy leak, isolation, enforcement — run on every package
upgrade). Tests prove the code runs; evals prove the system still finds and says the right
things.
