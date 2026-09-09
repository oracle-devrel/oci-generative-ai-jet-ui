from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path("docs/assets/ml_feature_pipeline.drawio")
OUT.parent.mkdir(parents=True, exist_ok=True)

cells: list[str] = []
edges: list[tuple[str, str, str]] = []


def cell(
    id_: str,
    value: str,
    x: int,
    y: int,
    w: int,
    h: int,
    fill: str,
    stroke: str = "#24405f",
    rounded: bool = True,
    font_size: int = 18,
    extra_style: str = "",
) -> None:
    style = (
        f"rounded={'1' if rounded else '0'};whiteSpace=wrap;html=1;"
        f"fillColor={fill};strokeColor={stroke};fontColor=#102033;"
        f"fontFamily=Inter;fontSize={font_size};spacing=12;arcSize=12;"
        f"{extra_style}"
    )
    cells.append(
        f'<mxCell id="{id_}" value="{escape(value)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />'
        "</mxCell>"
    )


def section(id_: str, value: str, x: int, y: int, w: int, h: int) -> None:
    cell(
        id_,
        value,
        x,
        y,
        w,
        h,
        "#f8fafc",
        "#cbd5e1",
        font_size=20,
        extra_style="fontStyle=1;",
    )


def note(id_: str, value: str, x: int, y: int, w: int, h: int) -> None:
    cell(id_, value, x, y, w, h, "#fff7d6", "#d6a800", font_size=16)


def edge(id_: str, source: str, target: str) -> None:
    edges.append((id_, source, target))


# Title and main ingestion row.
cell(
    "title",
    "<b>World Cup 2026 ML + Oracle Hybrid Retrieval Pipeline</b><br/>92-feature XGBoost built from chronological football trackers",
    160,
    20,
    1380,
    76,
    "#e8f0ff",
    "#4b6cb7",
    font_size=21,
)

cell(
    "data",
    "<b>Canonical Kaggle CSVs</b><br/>results.csv · goalscorers.csv · shootouts.csv<br/>49k+ matches, 47k+ goals, 675 shootouts",
    45,
    135,
    310,
    116,
    "#e7f7ed",
    "#2f855a",
)
cell(
    "oracle",
    "<b>Oracle AI Database</b><br/>MATCH_RESULTS · GOALSCORERS · SHOOTOUTS<br/>team statistics + competitive views",
    410,
    135,
    330,
    116,
    "#fdecec",
    "#c53030",
)
cell(
    "replay",
    "<b>Chronological tracker replay</b><br/>Extract pre-match state → emit row → update trackers<br/><i>No future leakage</i>",
    795,
    135,
    370,
    116,
    "#fff4e5",
    "#dd6b20",
)
cell(
    "factory",
    "<b>Feature factory</b><br/>Same tracker classes power training, cached predictions, and live <code>predict_match</code> inference.",
    1220,
    135,
    390,
    116,
    "#eef2ff",
    "#5a67d8",
)

# Central spine. Keeping one vertical path avoids draw.io auto-routing through text.
section("feature_summary", "Feature family extractors — 92 predictors assembled before each match update", 515, 305, 670, 64)
cell("row", "<b>Final model row</b><br/>92 numeric predictors<br/>same names in <code>enhanced_features.ALL_FEATURES</code> and <code>best_model.pkl</code>", 630, 410, 440, 112, "#eef2ff", "#5a67d8", font_size=17)
cell("split", "<b>Training protocol</b><br/>Use matches from 1990+<br/>time split: train &lt; 2020, test ≥ 2020", 630, 565, 440, 112, "#f7fafc", "#4a5568")
cell("models", "<b>Model progression</b><br/>Decision Tree → Random Forest → XGBoost / LightGBM<br/>Optuna + interactions + ensemble experiments", 630, 720, 440, 124, "#f7fafc", "#4a5568")
cell("artifact", "<b>Production artifact</b><br/>models/best_model.pkl<br/>classes: Win · Draw · Loss", 630, 890, 440, 112, "#e6fffa", "#319795")
cell("outputs", "<b>Inference outputs</b><br/><code>predict_match</code> live 92-feature row<br/>PREDICCIONES_FINAL cached matchups", 630, 1045, 440, 124, "#fdecec", "#c53030", font_size=17)
cell("lc", "<b>LangChain OracleVS hybrid store</b><br/>SOCCER_LANGCHAIN_DOCS via langchain-oracledb<br/>prediction docs + team facts + embeddings", 630, 1215, 440, 132, "#fdecec", "#c53030", font_size=17)
cell("retrieval", "<b>Final agent evidence path</b><br/>hybrid_retrieve = OracleHybridSearchRetriever when available<br/>fallback = Oracle Text + vector RRF", 630, 1395, 440, 124, "#e8f0ff", "#4b6cb7", font_size=17)

# Feature family cards are side annotations, not arrow targets.
cell("f0", "<b>Original baseline — 40</b><br/>Elo 8 · form/goals 19 · H2H 3 · context 10", 55, 410, 480, 112, "#eefbf3", "#2f855a")
cell("f1", "<b>Goalscorer intelligence — 12</b><br/>scoring depth · star dependency · penalties · late goals · first-half share", 55, 565, 480, 112, "#f0fff4", "#38a169")
cell("f4", "<b>Venue / geography — 5</b><br/>altitude · high-altitude flag · confederation strength · intercontinental", 55, 720, 480, 112, "#faf5ff", "#805ad5")
note("proof", "<b>No leakage rule</b><br/>For every historical match: read tracker state first, emit one feature row, then update trackers with the result.", 55, 890, 480, 112)

cell("f2", "<b>Momentum / psychology — 16</b><br/>streaks · unbeaten · clean sheets · comebacks · draw tendency · blowouts", 1165, 410, 480, 112, "#fffaf0", "#dd6b20")
cell("f3", "<b>Poisson xG — 8</b><br/>home/away λ · win/draw probabilities · variance · overperformance", 1165, 565, 480, 112, "#ebf8ff", "#3182ce")
cell("f5", "<b>Tournament context — 11</b><br/>World Cup form · competitive form · big-game factor · WC experience", 1165, 720, 480, 112, "#fef5e7", "#d69e2e")
note("elo", "<b>Elo scoring note</b><br/>Start 1500 · home +100 · K: WC 60 / continental 50 / qualifier 40 / friendly 20<br/>R_new = R_old + K×G×(actual−expected)", 1165, 890, 480, 132)

note(
    "callout",
    "<b>Workshop proof point</b><br/>Spain vs Brazil uses live 92-feature inference and can retrieve the matching prediction document from OracleVS hybrid search.",
    410,
    1565,
    880,
    82,
)

for eid, src, tgt in [
    ("e1", "data", "oracle"),
    ("e2", "oracle", "replay"),
    ("e3", "replay", "factory"),
    ("e4", "replay", "feature_summary"),
    ("e5", "feature_summary", "row"),
    ("e6", "row", "split"),
    ("e7", "split", "models"),
    ("e8", "models", "artifact"),
    ("e9", "artifact", "outputs"),
    ("e10", "outputs", "lc"),
    ("e11", "lc", "retrieval"),
    ("e12", "retrieval", "callout"),
]:
    edge(eid, src, tgt)

edge_xml = []
for eid, src, tgt in edges:
    style = (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
        "strokeWidth=3;strokeColor=#334155;endArrow=block;endFill=1;"
    )
    edge_xml.append(
        f'<mxCell id="{eid}" value="" style="{style}" edge="1" parent="1" source="{src}" target="{tgt}">'
        '<mxGeometry relative="1" as="geometry" />'
        "</mxCell>"
    )

xml = f'''<mxfile host="app.diagrams.net" modified="2026-06-10T00:00:00.000Z" agent="pi" version="24.7.17" type="device">
  <diagram id="ml-feature-pipeline" name="ML Feature Pipeline">
    <mxGraphModel dx="1700" dy="1680" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1700" pageHeight="1680" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        {''.join(cells)}
        {''.join(edge_xml)}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
'''
OUT.write_text(xml, encoding="utf-8")
print(OUT)
