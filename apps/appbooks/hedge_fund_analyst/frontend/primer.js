const $ = (s) => document.querySelector(s),
  esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
    );
const fmt = (row) =>
  Object.entries(row)
    .filter(([k]) => k !== "passed")
    .map(
      ([k, v]) =>
        "<span>" +
        esc(k) +
        ": <b>" +
        esc(typeof v === "number" ? v.toLocaleString() : v) +
        "</b></span>"
    )
    .join("<br>");
// Live proof: the same SQL under each desk's end user, plus that run's audit records.
$("#run-proof").onclick = async () => {
  const b = $("#run-proof");
  b.disabled = true;
  $("#proof-status").textContent = "Running as hf_credit and hf_markets…";
  try {
    const r = await fetch("/api/dds/evidence");
    const d = await r.json();
    if (!r.ok) throw Error(d.detail || "Request failed");
    const desks = Object.keys(d.results);
    let ok = 0,
      total = 0;
    let html =
      '<div class="proof"><div class="ph">Check (same SQL for both)</div>' +
      desks
        .map((p) => '<div class="ph">' + esc(p) + " · hf_" + esc(p.toLowerCase()) + "</div>")
        .join("");
    for (const c of d.checks) {
      html += '<div class="pl"><b>' + esc(c.label) + "</b><code>" + esc(c.sql) + "</code></div>";
      for (const p of desks) {
        const row = d.results[p][c.key];
        total++;
        if (row.passed) ok++;
        html +=
          '<div><span class="' +
          (row.passed ? "pass" : "fail") +
          '">' +
          (row.passed ? "✓ entitled" : "✗ FAILED") +
          "</span><br>" +
          fmt(row) +
          "</div>";
      }
    }
    html +=
      '</div><div class="audit-grid">' +
      desks
        .map((p) => {
          const rows = d.audit[p] || [];
          return (
            "<div><h3>Unified Audit · " +
            esc(p) +
            ' run <span class="muted">(' +
            rows.length +
            " records)</span></h3>" +
            (rows.length
              ? '<table class="ptable"><thead><tr><th>end user</th><th>action</th><th>object</th><th>time</th></tr></thead><tbody>' +
                rows
                  .slice(0, 10)
                  .map(
                    (a) =>
                      "<tr><td>" +
                      esc(a.end_user_name || a.dbusername) +
                      "</td><td>" +
                      esc(a.action_name) +
                      "</td><td>" +
                      esc(a.object_name) +
                      "</td><td>" +
                      esc((a.event_timestamp || "").slice(11, 23)) +
                      "</td></tr>"
                  )
                  .join("") +
                "</tbody></table>"
              : '<p class="muted">Audit records can take a moment to flush; run again to see them.</p>') +
            "</div>"
          );
        })
        .join("") +
      "</div>";
    $("#proof-out").innerHTML = html;
    $("#proof-status").textContent =
      ok + " of " + total + " results entitled correctly · run " + d.run;
  } catch (e) {
    $("#proof-status").textContent = e.message;
  } finally {
    b.disabled = false;
  }
};
// Check yourself: answers explain the reason, not just right or wrong.
const QUIZ = [
  {
    q: "The model writes SELECT * FROM HF_POSITIONS WHERE 1=1 while the Credit analyst is signed in. What comes back?",
    a: ["Both desks: the predicate is always true", "Only Credit rows", "An error"],
    right: 1,
    why: "The data grant adds desk = ‘Credit’ underneath the statement. The model’s predicate cannot widen it; the live proof runs exactly this case.",
  },
  {
    q: "Where should the desk filter live in an agent system?",
    a: [
      "In the prompt",
      "In the tool code (WHERE desk = :desk)",
      "In a data grant in the database",
    ],
    right: 2,
    why: "Prompts and tool code can be bypassed or forgotten on a new code path. A data grant applies to every statement for that end user.",
  },
  {
    q: "Why did the demo’s property graph first show both desks to each analyst?",
    a: [
      "A missing index",
      "Graph queries run with definer rights over base tables",
      "The analyst had a DBA role",
    ],
    right: 1,
    why: "Definer-rights objects read as their owner. Desk vertices now come from views keyed on the authenticated end user, and a live check verifies isolation.",
  },
  {
    q: "Can a DDS end user read through Oracle True Cache in this build?",
    a: ["Yes, transparently", "No, the logon fails with ORA-16000", "Only for SELECT *"],
    right: 1,
    why: "End-user logon writes session state the read-only instance cannot accept, so entitled reads stay on the primary.",
  },
  {
    q: "An agent connects with its own account. What does it need to act for a specific user (Pattern B)?",
    a: [
      "The user’s database password",
      "CREATE SESSION, CREATE END USER SECURITY CONTEXT, the user’s identity and an IAM database-access token over TLS",
      "A DBA role and a WHERE clause",
    ],
    right: 1,
    why: "The context payload carries the end-user identity and a database-access token; Oracle validates both and applies that user’s grants for the request.",
  },
];
$("#quiz-out").innerHTML = QUIZ.map(
  (x, i) =>
    '<div class="quiz-q" data-i="' +
    i +
    '"><p>' +
    (i + 1) +
    ". " +
    esc(x.q) +
    "</p>" +
    x.a.map((t, j) => '<button data-j="' + j + '">' + esc(t) + "</button>").join("") +
    '<div class="why" hidden></div></div>'
).join("");
document.querySelectorAll(".quiz-q button").forEach(
  (b) =>
    (b.onclick = () => {
      const box = b.closest(".quiz-q"),
        x = QUIZ[box.dataset.i],
        j = +b.dataset.j;
      box.querySelectorAll("button").forEach((o) => o.classList.remove("right", "wrong"));
      b.classList.add(j === x.right ? "right" : "wrong");
      box.querySelector('[data-j="' + x.right + '"]').classList.add("right");
      const w = box.querySelector(".why");
      w.hidden = false;
      w.textContent = (j === x.right ? "Correct. " : "Not quite. ") + x.why;
    })
);
