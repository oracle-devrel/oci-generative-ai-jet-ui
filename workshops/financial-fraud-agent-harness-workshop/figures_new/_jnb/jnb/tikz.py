"""TikZ -> SVG with the jnb preamble (New Computer Modern, token colours, cuboid helpers).

Route: ``lualatex --output-format=dvi`` -> ``dvisvgm --no-fonts --exact-bbox``.

* lualatex + fontspec/unicode-math load the New Computer Modern OTFs from ``assets/fonts``
  directly, so text and math use the real book fonts (no Latin Modern substitution).
* dvisvgm converts the DVI to SVG *without Ghostscript* because ``pgfsys-dvisvgm.def`` makes
  pgf emit dvisvgm-native specials. ``--no-fonts`` turns every glyph into a path, so the SVG
  renders identically everywhere (browsers, JupyterLab, VS Code, cairosvg) with no font
  files installed.
* System requirements: ``lualatex`` (Debian/Ubuntu: ``texlive-luatex``, ``texlive-latex-extra``,
  ``texlive-pictures``) and ``dvisvgm``.

Public API: :func:`tikz`, :func:`tikz_file`, :func:`register_magic` (``%%tikz``).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from .tokens import ASSETS, load_tokens

__all__ = ["tikz", "tikz_file", "tex_matrix", "register_magic", "TikZError", "preamble"]

CACHE = ASSETS.parent / "cache" / "tikz"
_TIMEOUT = 180


class TikZError(RuntimeError):
    """LaTeX or dvisvgm failed; the message holds only the relevant log lines."""


# --------------------------------------------------------------------------- preamble
group_prefix = {"roles": "", "text": "text-", "surface": "surface-", "greys": "grey-"}


def _colors_tex(tokens: dict) -> str:
    """One ``\\definecolor`` per colour token: roles ``jnb-input``, text ``jnb-text-body``,
    surface ``jnb-surface-bg``, greys ``jnb-grey-cuboid-top`` (underscores become hyphens)."""
    lines = []
    for group, prefix in group_prefix.items():
        for key, val in tokens.get(group, {}).items():
            if not (isinstance(val, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", val)):
                continue
            name = f"jnb-{prefix}{key.replace('_', '-')}"
            lines.append(f"\\definecolor{{{name}}}{{HTML}}{{{val[1:].upper()}}}")
    return "\n".join(lines)


def _fonts_tex(tokens: dict) -> str:
    """fontspec/unicode-math setup. Faces are picked by file name suffix, so reordering
    ``fonts.files`` in tokens.json cannot silently swap Regular/Italic."""
    fdir = (ASSETS / "fonts").as_posix() + "/"
    files = tokens["fonts"]["files"]

    def pick(group, *suffixes):
        for suf in suffixes:
            for f in files[group]:
                if f.endswith(f"-{suf}.otf"):
                    return f
        return None

    out = []
    for cmd, group, feats in (("setmainfont", "serif", ("Italic", "Bold", "BoldItalic")),
                              ("setsansfont", "sans", ("Oblique", "Bold", None)),
                              ("setmonofont", "mono", ("Italic", "Bold", None))):
        reg = pick(group, "Regular")
        opts = [f"Path={fdir}"]
        keys = ("ItalicFont", "BoldFont", "BoldItalicFont")
        for key, suf in zip(keys, feats):
            f = pick(group, suf) if suf else None
            if f:
                opts.append(f"{key}={f}")
        out.append(f"\\{cmd}{{{reg}}}[{','.join(opts)}]")
    out.append(f"\\setmathfont{{{pick('math', 'Regular')}}}[Path={fdir}]")
    return "\n".join(out)


def preamble(tokens: dict | None = None) -> str:
    """The full LaTeX preamble (up to, not including, ``\\begin{document}``)."""
    tokens = tokens or load_tokens()
    src = (ASSETS / "tikz" / "preamble.tex").read_text(encoding="utf-8")
    return (src.replace("@@COLORS@@", _colors_tex(tokens))
               .replace("@@FONTS@@", _fonts_tex(tokens)))


# --------------------------------------------------------------------------- compile
_BEGIN = re.compile(r"\\begin\{tikzpicture\}")


def _document(src: str, tokens: dict) -> tuple[str, int]:
    """Full LaTeX document and the number of lines preceding the user's source (so error
    line numbers can be reported relative to the figure source)."""
    wrapped = not _BEGIN.search(src)
    head = f"{preamble(tokens)}\n\\begin{{document}}\n" + ("\\begin{tikzpicture}\n" if wrapped else "")
    tail = "\n\\end{tikzpicture}" if wrapped else ""
    return f"{head}{src}{tail}\n\\end{{document}}\n", head.count("\n")


def _log_errors(log: str, offset: int = 0) -> str:
    """Only the ``!`` error blocks: the error line(s) up to and including the ``l.<n>``
    source-context line and the one after it."""
    lines = log.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("!") and "Fatal error occurred" not in lines[i]:
            j = i
            while j < len(lines) and j < i + 15 and not lines[j].startswith("l."):
                j += 1
            block = [ln for ln in lines[i:j + 2] if ln.strip() and not ln.startswith("See the ")
                     and not ln.startswith("Type  H")]
            block = [re.sub(r"^l\.(\d+)", lambda m: f"l.{int(m.group(1)) - offset} (figure source)", ln)
                     for ln in block]
            out.extend(block + [""])
            i = j + 2
        else:
            i += 1
    text = "\n".join(out).strip() or "\n".join(lines[-15:])
    if re.search(r"luatex85\.sty. not found|luaotfload-main. not found", log):
        text += ("\n\nhint: a TeX Live LuaTeX component is missing "
                 "(Debian/Ubuntu: sudo apt-get install texlive-luatex).")
    return text


def _need(binary: str, hint: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise TikZError(f"`{binary}` not found on PATH ({hint})")
    return path


def _compile(tex: str, offset: int = 0) -> str:
    lualatex = _need("lualatex", "Debian/Ubuntu: sudo apt-get install texlive-luatex texlive-latex-extra texlive-pictures")
    dvisvgm = _need("dvisvgm", "Debian/Ubuntu: sudo apt-get install texlive-binaries (dvisvgm)")
    with tempfile.TemporaryDirectory(prefix="jnb-tikz-") as td:
        td = Path(td)
        (td / "fig.tex").write_text(tex, encoding="utf-8")
        try:
            r = subprocess.run(
                [lualatex, "--output-format=dvi", "-interaction=nonstopmode", "-halt-on-error",
                 "-no-shell-escape", "fig.tex"],
                cwd=td, capture_output=True, text=True, timeout=_TIMEOUT, errors="replace")
        except subprocess.TimeoutExpired:
            raise TikZError(f"lualatex timed out after {_TIMEOUT}s") from None
        log_path = td / "fig.log"
        log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else r.stdout
        if r.returncode != 0 or not (td / "fig.dvi").exists():
            raise TikZError("LaTeX failed:\n" + _log_errors(log, offset))
        r = subprocess.run(
            [dvisvgm, "--no-fonts", "--exact-bbox", "--precision=3", "-o", "fig.svg", "fig.dvi"],
            cwd=td, capture_output=True, text=True, timeout=_TIMEOUT, errors="replace")
        if r.returncode != 0 or not (td / "fig.svg").exists():
            raise TikZError("dvisvgm failed:\n" + (r.stderr or r.stdout)[-1500:])
        return (td / "fig.svg").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- SVG cleanup
_SVG_OPEN = re.compile(r"<svg\b[^>]*>")


def _finish_svg(svg: str, uid: str, scale: float, bg: str | None) -> str:
    """Make the SVG safe to inline: drop prolog/comments, uniquify ids, apply scale/bg."""
    svg = re.sub(r"<\?xml[^>]*\?>\s*", "", svg)
    svg = re.sub(r"<!--.*?-->\s*", "", svg, flags=re.S)
    # dvisvgm ids (glyph paths, clip paths, ...) would collide between inline figures
    ids = set(re.findall(r"\bid=['\"]([^'\"]+)['\"]", svg))
    if ids:
        pat = re.compile("|".join(re.escape(i) for i in sorted(ids, key=len, reverse=True)))
        svg = re.sub(r"(\bid=['\"])(%s)(['\"])" % pat.pattern, rf"\g<1>{uid}-\g<2>\g<3>", svg)
        svg = re.sub(r"((?:href=['\"]|url\()#)(%s)(?=['\")])" % pat.pattern, rf"\g<1>{uid}-\g<2>", svg)
    m = _SVG_OPEN.search(svg)
    if not m:
        raise TikZError("dvisvgm produced no <svg> element")
    tag = m.group(0)
    new = tag
    if scale != 1.0:
        def mul(mm):
            return f"{mm.group(1)}{float(mm.group(2)) * scale:.4f}{mm.group(3)}"
        new = re.sub(r"(\bwidth=['\"])([\d.]+)([a-z]*['\"])", mul, new)
        new = re.sub(r"(\bheight=['\"])([\d.]+)([a-z]*['\"])", mul, new)
    new = new[:-1] + ' class="jnb-tikz" role="img">'
    rect = ""
    if bg:
        vb = re.search(r"viewBox=['\"]([-\d. ]+)['\"]", tag)
        if vb:
            x, y, w, h = vb.group(1).split()
            rect = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{bg}"/>'
    return svg[:m.start()] + new + rect + svg[m.end():]


# --------------------------------------------------------------------------- public API
def tikz(src: str, name: str | None = None, scale: float = 1.0, bg: bool = False) -> str:
    """Compile TikZ to SVG text.

    ``src`` is either the contents of a tikzpicture or a full
    ``\\begin{tikzpicture}...\\end{tikzpicture}`` (macros such as ``\\inp`` and
    ``\\jnbcuboid`` are available; see assets/tikz/preamble.tex). ``name`` only labels the
    cache file. ``scale`` multiplies the SVG's display size (fonts included, geometry
    unchanged). ``bg=True`` paints ``surface.bg`` behind the figure (default transparent).
    Results are cached in ``<ASSETS>/../cache/tikz`` keyed by sha256(source, preamble,
    tokens, scale, bg).
    """
    tokens = load_tokens()
    doc, offset = _document(src, tokens)
    bgcolor = tokens["surface"]["bg"] if bg else None
    key = hashlib.sha256("\0".join([doc, repr(tokens), repr(float(scale)), str(bgcolor)]).encode()).hexdigest()
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-") if name else "fig"
    path = CACHE / f"{safe}-{key[:16]}.svg"
    if path.exists():
        return path.read_text(encoding="utf-8")
    svg = _finish_svg(_compile(doc, offset), f"jnb{key[:8]}", float(scale), bgcolor)
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(svg, encoding="utf-8")
    tmp.replace(path)
    return svg


def tex_matrix(P, fmt: str = "{:g}") -> str:
    """2-D array -> ``{{a,b},{c,d}}``, the argument format of ``\\jnbbars``/``\\jnbmatrix``."""
    return "{" + ",".join("{" + ",".join(fmt.format(float(x)) for x in row) + "}" for row in P) + "}"


def tikz_file(path, name: str | None = None, scale: float = 1.0, bg: bool = False,
              subs: dict | None = None) -> str:
    """Compile a ``.tex`` file containing a tikzpicture (see :func:`tikz`).

    ``subs`` replaces ``<<KEY>>`` placeholders before compiling, so the figure can be
    driven by notebook data: ``subs={"P": tex_matrix(P)}`` fills ``\\jnbbars<<P>>``."""
    p = Path(path)
    src = p.read_text(encoding="utf-8")
    for key, val in (subs or {}).items():
        token = f"<<{key}>>"
        if token not in src:
            raise KeyError(f"placeholder {token} not found in {p}")
        src = src.replace(token, str(val))
    return tikz(src, name=name or p.stem, scale=scale, bg=bg)


# --------------------------------------------------------------------------- %%tikz magic
def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="%%tikz", add_help=False)
    ap.add_argument("--name")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--caption")
    ap.add_argument("--bg", action="store_true")
    return ap


def _show(svg: str, caption: str | None) -> None:
    try:
        from jnb import figure
    except ImportError:
        from IPython.display import SVG, display
        display(SVG(svg))
        return
    figure(svg, caption=caption)


def register_magic() -> None:
    """Register ``%%tikz [--name N] [--scale S] [--caption "..."] [--bg]`` if IPython runs."""
    try:
        from IPython import get_ipython
        from IPython.core.error import UsageError
    except ImportError:
        return
    ip = get_ipython()
    if ip is None:
        return

    def tikz_magic(line, cell):
        try:
            args = _parser().parse_args(shlex.split(line))
        except SystemExit:
            raise UsageError('usage: %%tikz [--name N] [--scale S] [--caption "..."] [--bg]') from None
        _show(tikz(cell, name=args.name, scale=args.scale, bg=args.bg), args.caption)

    ip.register_magic_function(tikz_magic, "cell", "tikz")
