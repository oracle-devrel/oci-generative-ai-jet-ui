"""Figure 2.1 -- schematic geometry of a query and its nearest facts (no sample-run values)."""
import math

# schematic distances only: distance = VECTOR_DISTANCE(..., COSINE) = 1 - cos(theta)
HITS = [  # (label line1, line2, schematic distance)
    ("transactions.amount_cents", "meaning", 0.30),
    ("transactions.amount_cents", "unit", 0.45),
    ("FINANCE.TRANSACTIONS", ".AMOUNT_CENTS", 0.60),
]
QUERY = "monetary denomination scale"
E_DEG = 30.0                 # camera elevation
AZ = [180.0, 90.0, 0.0]    # illustrative azimuth of each fact around q (the angle to q is exact)
R = 3.3
A_DEG = 22.0                 # q is tilted this far above the horizontal axis
_a = math.radians(A_DEG)
U = (math.cos(_a), 0.0, math.sin(_a))      # q
V = (-math.sin(_a), 0.0, math.cos(_a))     # two unit vectors orthogonal to q
W = (0.0, 1.0, 0.0)

def project(v, e=math.radians(E_DEG)):
    x, y, z = v
    return (R * x, R * (z * math.cos(e) + y * math.sin(e)), y * math.cos(e) - z * math.sin(e))

def fact_vec(theta, phi):
    p = math.radians(phi)
    return tuple(math.cos(theta) * U[i] + math.sin(theta) * (math.cos(p) * V[i] + math.sin(p) * W[i]) for i in range(3))

def slerp(a, b, n=24):
    dot = sum(i * j for i, j in zip(a, b)); w = math.acos(max(-1, min(1, dot)))
    out = []
    for k in range(n + 1):
        t = k / n
        s0, s1 = math.sin((1 - t) * w) / math.sin(w), math.sin(t * w) / math.sin(w)
        out.append(tuple(s0 * i + s1 * j for i, j in zip(a, b)))
    return out

def pt(p):
    return f"({p[0]:.3f},{p[1]:.3f})"

def build_tex():
    q = U
    thetas = [math.acos(1 - d) for _, _, d in HITS]
    L = []
    L.append(r"""\newcommand{\subl}[1]{{\footnotesize\textcolor{jnb-text-muted}{#1}}}
\begin{tikzpicture}[lab/.style={font=\footnotesize, text=jnb-text-muted, inner sep=2pt}]
\path[use as bounding box] (-6.4,-8.2) rectangle (20.4,5.4);
""")
    # sphere silhouette + equator (back dashed, front solid)
    L.append(f"\\draw[draw=jnb-grey-cell-edge, line width=0.8pt] (0,0) circle ({R});")
    e = math.radians(E_DEG)
    back = [(R * math.cos(t), R * math.sin(t) * math.sin(e)) for t in [math.pi * i / 60 for i in range(61)]]
    front = [(R * math.cos(t), -R * math.sin(t) * math.sin(e)) for t in [math.pi * i / 60 for i in range(61)]]
    L.append("\\draw[draw=jnb-grey-cell-edge, line width=0.6pt, dashed] plot[smooth] coordinates {" + " ".join(pt(p) for p in back) + "};")
    L.append("\\draw[draw=jnb-grey-cell-edge, line width=0.6pt] plot[smooth] coordinates {" + " ".join(pt(p) for p in front) + "};")
    # geodesics
    for i, th in enumerate(thetas):
        f = fact_vec(th, AZ[i])
        arc = [project(v)[:2] for v in slerp(q, f)]
        col = "jnb-highlight" if i == 0 else "jnb-text-muted"
        L.append(f"\\draw[draw={col}, line width=0.9pt, dash pattern=on 2pt off 2pt] plot[smooth] coordinates {{" + " ".join(pt(p) for p in arc) + "};")
    # fact vectors
    tips = []
    for i, th in enumerate(thetas):
        f = fact_vec(th, AZ[i]); s = project(f); tips.append((s, th))
        col = "jnb-highlight" if i == 0 else "jnb-third"
        w = "1.8pt" if i == 0 else "1.4pt"
        L.append(f"\\draw[draw={col}, line width={w}, ->] (0,0) -- {pt(s)};")
    # query vector
    qs = project(q)
    L.append(f"\\draw[inp arrow, line width=2pt] (0,0) -- {pt(qs)};")
    L.append("\\fill[jnb-text-body] (0,0) circle (1.8pt);")
    L.append(f"\\node[inp, anchor=west, align=left, font=\\normalsize] at ({qs[0]+0.25:.3f},{qs[1]-0.1:.3f}) {{$\\inp{{\\mathbf{{q}}}}$\\ \\subl{{``{QUERY}''}}}};")
    # fact labels (name on two lines + the exact angle to q)
    place = [(0.3, -0.1, "west", "left"), (0.1, 0.75, "south west", "left"), (-0.35, 0.35, "south east", "right")]
    for i, ((sx, th), (l1, l2, d)) in enumerate(zip(tips, HITS)):
        col = "jnb-highlight" if i == 0 else "jnb-third"
        ox, oy, anchor, al = place[i]
        e1, e2 = l1.replace('_', '\\_'), l2.replace('_', '\\_')
        L.append(f"\\node[font=\\footnotesize, anchor={anchor}, align={al}, text={col}] at ({sx[0]+ox:.3f},{sx[1]+oy:.3f}) "
                 f"{{\\texttt{{{e1}}}\\\\\\texttt{{{e2}}}}};")
    L.append(f"\\node[lab, anchor=north, align=center] at (0,{-R-0.35}) {{384\\,dims drawn on a sphere\\\\{{\\scriptsize\\textit{{schematic: only the angle to $\\inp{{\\mathbf{{q}}}}$ matters}}}}}};")

    # ---------------- right: distance ruler
    X0, W, Y0 = 8.6, 8.4, -0.6
    L.append(f"\\draw[draw=jnb-text-muted, line width=1pt] ({X0},{Y0}) -- ({X0+W},{Y0});")
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        L.append(f"\\draw[draw=jnb-text-muted, line width=0.8pt] ({X0+W*t:.3f},{Y0}) -- ({X0+W*t:.3f},{Y0-0.18});")
        L.append(f"\\node[lab, anchor=north] at ({X0+W*t:.3f},{Y0-0.2}) {{{t:g}}};")
    L.append(f"\\node[font=\\small, text=jnb-fourth, anchor=north] at ({X0+W/2},{Y0-1.05}) {{$\\fourth{{d}}$ = cosine distance}};")
    L.append(f"\\node[lab, anchor=north, align=center] at ({X0+W/2},{Y0-1.65}) {{$d=0$ same direction $\\cdot$ $d=1$ orthogonal ($\\theta=90^\\circ$)}};")
    # query marker at d=0
    L.append(f"\\fill[jnb-input] ({X0},{Y0}) circle (3pt);")
    L.append(f"\\node[inp, anchor=south, font=\\small] at ({X0},{Y0+0.25}) {{$\\inp{{\\mathbf{{q}}}}$}};")
    lead = [(-1.0, 1.15), (0.0, 2.35), (1.0, 1.15)]
    for i, (l1, l2, d) in enumerate(HITS):
        x = X0 + W * d
        col = "jnb-highlight" if i == 0 else "jnb-third"
        dxl, hl = lead[i]
        L.append(f"\\fill[{col}] ({x:.3f},{Y0}) circle ({3.6 if i==0 else 3}pt);")
        L.append(f"\\draw[draw={col}, line width=0.8pt] ({x:.3f},{Y0+0.08}) -- ({x+dxl*0.7:.3f},{Y0+hl});")
        anc = "east" if dxl < 0 else ("west" if dxl > 0 else "south")
        pos = (x + dxl * 0.7 + dxl * 0.08, Y0 + hl) if dxl else (x, Y0 + hl + 0.05)
        L.append(f"\\node[font=\\small, anchor={anc}, text={'jnb-highlight' if i==0 else 'jnb-third'}] at ({pos[0]:.3f},{pos[1]:.3f}) {{$\\mathbf{{f}}_{i+1}$}};")
    L.append(f"\\node[lab, anchor=north west, align=left] at ({X0},{Y0-2.6}) "
             "{smaller $d$ is closer: a fact can rank first with no word in common};")
    L.append(f"\\node[lab, anchor=north west, align=left] at ({X0},{Y0-3.4}) "
             "{ranked by $d$, i.e.\\ by the angle at the origin};")
    # equation
    L.append("\\node[font=\\large] at (7.2,-7.2) {%\n  $\\fourth{d}(\\inp{\\mathbf{q}},\\third{\\mathbf{f}})\\;=\\;1-\\cos\\theta\\;=\\;1-"
             "\\dfrac{\\inp{\\mathbf{q}}\\cdot\\third{\\mathbf{f}}}{\\lVert\\inp{\\mathbf{q}}\\rVert\\,\\lVert\\third{\\mathbf{f}}\\rVert}$};")
    L.append("\\end{tikzpicture}")
    return "\n".join(L)

if __name__ == "__main__":
    print(build_tex())
