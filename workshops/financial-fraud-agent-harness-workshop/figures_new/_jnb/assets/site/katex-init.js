// KaTeX auto-render for $…$, $$…$$, \(…\), \[…\]. Role macros (\inp, \out, \hl, …)
// come from macros.js, which render_site.py generates from tokens.json.
document.addEventListener("DOMContentLoaded", function () {
  if (typeof renderMathInElement !== "function") return;
  renderMathInElement(document.body, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "\\begin{equation}", right: "\\end{equation}", display: true },
      { left: "\\begin{align}", right: "\\end{align}", display: true },
      { left: "\\begin{align*}", right: "\\end{align*}", display: true },
      { left: "\\[", right: "\\]", display: true },
      { left: "$", right: "$", display: false },
      { left: "\\(", right: "\\)", display: false },
    ],
    macros: window.JNB_KATEX_MACROS || {},
    throwOnError: false,
    ignoredClasses: ["highlight", "jnb-no-math"],
  });
  document.documentElement.setAttribute("data-jnb-math", "done");
});
