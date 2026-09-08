from __future__ import annotations


def build_css_snippet() -> str:
    return """
body {
  --limitless-green: #8dff8a;
  --limitless-green-soft: #69d884;
  --limitless-panel: rgba(13, 28, 18, 0.82);
  --limitless-panel-border: rgba(141, 255, 138, 0.20);
  --limitless-panel-strong: rgba(141, 255, 138, 0.28);
  --limitless-bg: #08110b;
  --limitless-text: #d7f6d3;
  --limitless-muted: #9dc49a;
}

.theme-dark {
  --background-primary: #08110b;
  --background-secondary: #0d1610;
  --text-normal: var(--limitless-text);
  --text-muted: var(--limitless-muted);
  --interactive-accent: var(--limitless-green-soft);
}

.markdown-preview-view.cognitive-vault,
.markdown-source-view.mod-cm6.cognitive-vault {
  color: var(--limitless-text);
}

.cognitive-vault .vault-strip,
.cognitive-vault .vault-grid,
.cognitive-vault .vault-panel,
.cognitive-vault .concept-card {
  border: 1px solid var(--limitless-panel-border);
  background: var(--limitless-panel);
  border-radius: 16px;
  padding: 1rem 1.1rem;
  box-shadow: 0 0 0 1px rgba(141,255,138,0.04), 0 0 24px rgba(65,166,96,0.08);
}

.cognitive-vault .vault-strip {
  margin: 1rem 0 1.2rem;
}

.cognitive-vault .vault-grid {
  display: grid;
  gap: 1rem;
  margin: 1rem 0;
}

.cognitive-vault .vault-grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.cognitive-vault .vault-grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.cognitive-vault .vault-panel.hero {
  border-color: var(--limitless-panel-strong);
}

.cognitive-vault .eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.72rem;
  color: var(--limitless-green);
  margin-bottom: 0.35rem;
  font-weight: 700;
}

.cognitive-vault .metric {
  font-size: 1.45rem;
  font-weight: 800;
}

.cognitive-vault .muted {
  color: var(--limitless-muted);
}

.cognitive-vault .trend-up { color: #7cfb88; font-weight: 700; }
.cognitive-vault .trend-down { color: #ffd36e; font-weight: 700; }
.cognitive-vault .trend-flat { color: var(--limitless-muted); font-weight: 700; }

.cognitive-vault .band {
  display: inline-block;
  padding: 0.22rem 0.6rem;
  border-radius: 999px;
  border: 1px solid var(--limitless-panel-border);
  font-size: 0.78rem;
  margin-right: 0.35rem;
}

.cognitive-vault .band-Fragile { color: #ffd36e; }
.cognitive-vault .band-Developing { color: #9fe7ff; }
.cognitive-vault .band-Solid { color: #9df5b0; }
.cognitive-vault .band-Strong { color: #7cfb88; }
.cognitive-vault .band-Unassessed { color: var(--limitless-muted); }

.cognitive-vault.dashboard h1,
.cognitive-vault.topic-note h1,
.cognitive-vault.concept-note h1,
.cognitive-vault.session-note h1 {
  border-bottom: 1px solid var(--limitless-panel-border);
  padding-bottom: 0.4rem;
}

.cognitive-vault .session-snippet {
  font-style: italic;
  color: #dff7d7;
}

.cognitive-vault .link-list li {
  margin: 0.18rem 0;
}

@media (max-width: 900px) {
  .cognitive-vault .vault-grid.two,
  .cognitive-vault .vault-grid.three {
    grid-template-columns: 1fr;
  }
}
""".strip() + "\n"
