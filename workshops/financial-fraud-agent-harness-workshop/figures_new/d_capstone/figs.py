"""TikZ sources for the Part 6 figure (schematic: no sample-run data)."""


# --------------------------------------------------------------------------- helpers
def tt(s):
    """Escape a literal for \\texttt{...} / \\mathtt{...}."""
    for a, b in (("\\", r"\textbackslash{}"), ("_", r"\_"), ("$", r"\$"), ("&", r"\&"), ("#", r"\#"),
                 ("%", r"\%"), ("{", r"\{"), ("}", r"\}")):
        s = s.replace(a, b)
    return hy(s)


def hy(s):
    """Plain '-' (and \\symbol{45}) render as nothing through dvi->svg with NCM: use U+2010."""
    return s.replace("-", r'\char"2010{}')


def T(s):
    return rf"\texttt{{{tt(s)}}}"


def pad(x0, y0, x1, y1):
    """Extend the bounding box (and so the baked-in background) around the drawing."""
    return rf"\path ({x0},{y0}) ({x1},{y1});"




# =========================================================================== 6.1
def tikz_loop():
    third = "draw=jnb-third, fill=jnb-third!22!jnb-surface-bg, line width=1.4pt"
    return rf"""\begin{{tikzpicture}}[box/.style={{align=center, inner sep=4pt, font=\footnotesize}}]
{pad(-0.3, 2.6, 17.0, -6.9)}
% ---- the triage run (§6.3)
\node[muted, anchor=west, font=\footnotesize] at (0,2.05) {{triage run, §6.3}};
\node[box, jnb cell inp, minimum width=2.6cm, minimum height=1.5cm] (A) at (1.3,0) {{\inp{{alert}}\\\inp{{+ evidence pack}}}};
\node[box, jnb cell, minimum width=2.8cm, minimum height=1.5cm] (B) at (4.8,0) {{agent loop\\$\le 6$ iterations\\$\le 120$ s}};
\node[box, jnb cell out, minimum width=2.8cm, minimum height=1.5cm] (C) at (8.8,0) {{\out{{validated}}\\\out{{decision}}}};
\draw[inp arrow] (A) -- (B);
\draw[->, line width=1pt] (B) -- (C);
% ---- two writes, on purpose
\node[box, {third}, minimum width=4.8cm, minimum height=1.9cm] (L) at (14.3,1.2) {{%
  \third{{{T('AGENT.AML_TRIAGE')}}}\\ one row per $(c,k)$\\ for the examiner, read with SQL}};
\node[box, {third}, minimum width=4.8cm, minimum height=1.9cm] (M) at (14.3,-1.2) {{%
  \third{{OAMP memory}}\\ case decision, one per case\\ {{\scriptsize{T('case:<customer>:<typology>')}}}\\ for the agent, next time}};
\draw[->, line width=1pt] (C.east) -- ++(0.9,0) |- (L.west);
\draw[->, line width=1pt] (C.east) -- ++(0.9,0) |- (M.west);
% ---- next question (§6.4)
\node[muted, anchor=west, font=\footnotesize] at (0,-2.7) {{later, same thread, §6.4}};
\node[box, jnb cell inp, minimum width=2.6cm, minimum height=1.5cm] (Q) at (1.3,-4.6) {{\inp{{question}}\\\inp{{which cases did}}\\\inp{{you escalate?}}}};
\node[box, jnb cell, minimum width=2.8cm, minimum height=1.5cm] (B2) at (4.8,-4.6) {{agent loop\\same loop,\\new job}};
\node[box, jnb cell out, minimum width=2.8cm, minimum height=1.5cm] (R) at (8.8,-4.6) {{\out{{answer from}}\\\out{{the recorded}}\\\out{{decisions}}}};
\draw[inp arrow] (Q) -- (B2);
\draw[->, line width=1pt] (B2) -- (R);
\draw[hl, line width=1.6pt, dashed, ->] (M.south) -- ++(0,-0.95) -| (B2.north);
\node[hl, anchor=south, font=\small] at (9.8,-3.04) {{recall}};
\node[font=\normalsize, anchor=north] at (8.2,-5.7) {{%
  $\out{{\mathrm{{record}}_{{c,k}}}}\to\bigl(\third{{\mathrm{{AML\_TRIAGE}}[c,k]}},\ \third{{\mathrm{{memory}}}}\bigr),\qquad
  \hl{{\mathrm{{recall}}}}(q)=\mathrm{{agent\ loop}}\bigl(q\mid\third{{\mathrm{{memory}}}}\bigr)$}};
\end{{tikzpicture}}"""


FIGURES = [dict(
    number="6.1", slug="record-and-recall", anchor="## 6.3 Triage the queue", tikz=tikz_loop,
    caption="Record and recall. One validated decision is written to two places; later, dashed, a question is answered from the agent's memory.",
    prose="Figure 6.1 shows the two writes of one decision and the later recall.")]
