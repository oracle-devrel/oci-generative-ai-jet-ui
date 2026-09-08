<p align="center">
  <img src="assets/tui-splash.png" alt="Agent Reasoning TUI Splash" width="600"/>
</p>

<h1 align="center">Agent Reasoning: The Thinking Layer</h1>

<p align="center"><strong>Transform standard open-source LLMs into reliable problem solvers with 16 advanced cognitive architectures. From predicting the next token to predicting the next thought.</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Backend-Ollama-black?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama"/>
  <img src="https://img.shields.io/badge/Reasoning-16%20Strategies-purple?style=for-the-badge" alt="Reasoning"/>
  <a href="https://pypi.org/project/agent-reasoning/"><img src="https://img.shields.io/pypi/v/agent-reasoning?style=for-the-badge" alt="PyPI"/></a>
  <a href="https://pypi.org/project/agent-reasoning/"><img src="https://img.shields.io/pypi/dm/agent-reasoning?style=for-the-badge" alt="PyPI Downloads"/></a>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"/>
  <img src="https://img.shields.io/badge/Status-Experimental-orange?style=for-the-badge" alt="Status"/>
</p>

---

<table>
  <tr>
    <td align="center"><strong>Title</strong><br><img src="docs/slides/slide-01.png" alt="Title" width="400"/></td>
    <td align="center"><strong>Overview</strong><br><img src="docs/slides/slide-02.png" alt="Overview" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><strong>Architecture</strong><br><img src="docs/slides/slide-03.png" alt="Architecture" width="400"/></td>
    <td align="center"><strong>Features</strong><br><img src="docs/slides/slide-04.png" alt="Features" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><strong>Tech Stack</strong><br><img src="docs/slides/slide-05.png" alt="Tech Stack" width="400"/></td>
    <td align="center"><strong>Getting Started</strong><br><img src="docs/slides/slide-06.png" alt="Getting Started" width="400"/></td>
  </tr>
</table>

<p align="center">
  <a href="https://jasperan.github.io/agent-reasoning/interactive/">Explore the Interactive Explorer &rarr;</a>
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="docs/slides/presentation.html">View Interactive Presentation &rarr;</a>
</p>

## Installation

<!-- one-command-install -->
> **One-command install**: clone, configure, and run in a single step.
>
> ```bash
> curl -fsSL https://raw.githubusercontent.com/jasperan/agent-reasoning/main/install.sh | bash
> ```
>
> <details><summary>Advanced options</summary>
>
> Override install location:
> ```bash
> PROJECT_DIR=/opt/myapp curl -fsSL https://raw.githubusercontent.com/jasperan/agent-reasoning/main/install.sh | bash
> ```
>
> Or install manually:
> ```bash
> git clone https://github.com/jasperan/agent-reasoning.git
> cd agent-reasoning
> # See below for setup instructions
> ```
> </details>


## Vision & Purpose

The **Reasoning Layer** is the cognitive engine of the AI stack. While traditional LLMs excel at token generation, they often struggle with complex planning, logical deduction, and self-correction.

This repository transforms standard Open Source models (like `gemma3`, `llama3`) into reliable problem solvers by wrapping them in advanced cognitive architectures. It implements findings from key research papers (CoT, ToT, ReAct) to give models "agency" over their thinking process.

> **"From predicting the next token to predicting the next thought."**

---

## Quick Start (3 commands)

```bash
uv sync && ollama pull gemma3:270m && uv run agent-reasoning
```

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install agent-reasoning
# or
uv add agent-reasoning

# With server dependencies (for the reasoning gateway):
pip install "agent-reasoning[server]"
# or
uv add "agent-reasoning[server]"
```

### From Source with uv

```bash
git clone https://github.com/jasperan/agent-reasoning.git
cd agent-reasoning
uv sync
uv run agent-reasoning
```

### Development

```bash
# Sync dependencies
uv sync

# Run tests
uv run pytest

# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run ty check .

# Add a new dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>
```

**Prerequisite**: [Ollama](https://ollama.com/) must be running locally, or you can connect to a remote Ollama instance.
```bash
ollama pull gemma3:270m    # Tiny model for quick testing
ollama pull qwen3.5:9b    # Recommended model for quality results
```

### Configuring Remote Ollama Endpoint

If you don't have Ollama installed locally, you can connect to a remote Ollama instance. Configuration is stored in `config.yaml` in the root directory of the repository.

**Option 1: Interactive CLI Configuration**
```bash
agent-reasoning
# Select "Configure Endpoint" from the menu
```

**Option 2: Server CLI Argument**
```bash
agent-reasoning-server --ollama-host http://192.168.1.100:11434
```

**Option 3: Direct Config File**

Copy the example config and edit it:
```bash
cp config.yaml.example config.yaml
```

Or create `config.yaml` in the project root:
```yaml
ollama:
  host: http://192.168.1.100:11434
```

**Option 4: Python API**
```python
from agent_reasoning import ReasoningInterceptor, set_ollama_host, get_ollama_host

# Check current endpoint
print(get_ollama_host())  # http://localhost:11434

# Set a new endpoint (persists to config file)
set_ollama_host("http://192.168.1.100:11434")

# Or specify directly without saving to config
client = ReasoningInterceptor(host="http://192.168.1.100:11434")
```

---

## 📓 Notebooks

Interactive Jupyter notebooks demonstrating agent reasoning capabilities:

| Name | Description | Stack | Link |
| ---- | ----------- | ----- | ---- |
| agent_reasoning_demo | Comprehensive demo of all reasoning strategies (CoT, ToT, ReAct, Self-Reflection) with benchmarks and comparisons | Ollama, Gemma3/Llama3, FastAPI | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=for-the-badge)](https://github.com/jasperan/agent-reasoning/blob/main/notebooks/agent_reasoning_demo.ipynb) |

---

## 🚀 Features
**✅ Verified against ArXiv Papers**

*   **Plug & Play**: Use via Python Class or as a Network Proxy.
*   **Model Agnostic**: Works with any model served by Ollama.
*   **Advanced Architectures**:
    *   🔗 **Chain-of-Thought (CoT)** & **Self-Consistency**: Implements Majority Voting ($k$ samples) with temperature sampling.
    *   🌳 **Tree of Thoughts (ToT)**: BFS strategy with reliable heuristic scoring and pruning.
    *   🛠️ **ReAct (Reason + Act)**: Real-time tool usage (**Web Search** via scraping, Wikipedia API, Calculator) with fallback/mock capabilities. External grounding implemented.
    *   🪞 **Self-Reflection**: Dynamic multi-turn Refinement Loop (Draft -> Critique -> Improve).
    *   🧩 **Decomposition & Least-to-Most**: Planning and sub-task execution.
    *   🔄 **Refinement Loop**: Score-based iterative improvement (Generator → Critic → Refiner) until quality threshold met.
    *   📊 **Complex Refinement Pipeline**: 5-stage optimization (Technical Accuracy → Structure → Depth → Examples → Polish).

---

## 💻 Usage

### 1. Interactive CLI (Recommended)
Access all agents, comparisons, and benchmarks via the rich CLI.

```bash
# If installed via pip:
agent-reasoning

# Or from source:
python agent_cli.py
```

**CLI Shortcuts:**
```bash
python agent_cli.py                  # Full interactive menu
python agent_cli.py --arena          # Jump to arena mode
python agent_cli.py --benchmark      # Jump to benchmarks
python agent_cli.py --head-to-head   # Compare two agents
python agent_cli.py --agents         # Show strategy guide
```

**Interactive Experience:**
```text
╭────────────────────────────────────────────╮
│ AGENT REASONING CLI                        │
│ Advanced Cognitive Architectures (Gemma 3) │
╰────────────────────────────────────────────╯

? Select an Activity:
  Standard Agent - Direct generation
  Chain of Thought (CoT) - Step-by-step reasoning
  Tree of Thoughts (ToT) - Branching exploration
  ReAct (Tools + Web) - Reason + Act
  Recursive (RLM) - Code REPL agent
  Self-Reflection - Draft/critique/refine
  Decomposed - Sub-task breakdown
  Least-to-Most - Easy to hard
  Self-Consistency - Majority voting
  ──────────────────
  🔄 Refinement Loop [Auto Demo]
  🔄 Complex Pipeline [5 Stages]
  ──────────────────
  🔀 HEAD-TO-HEAD: Compare Two Agents
  ⚔️  ARENA: Run All Compare
  📊 BENCHMARKS: Performance Testing
  ──────────────────
  ℹ️  About Agents (Strategy Guide)
  📂 Session History
  ⚙️  Select AI Model
  Exit
```

**New Features:**
- **Timing Metrics**: Every response shows TTFT, total time, tokens/sec
- **Session History**: All chats auto-saved to `data/sessions/` with export to markdown
- **Head-to-Head**: Compare any two strategies side-by-side in parallel
- **Agent Info**: Built-in strategy guide with descriptions and use cases
- **Benchmark Charts**: Auto-generate PNG visualizations of benchmark results

### 2. Terminal UI (TUI)

A Go-based terminal interface built with [Bubble Tea](https://github.com/charmbracelet/bubbletea) + [Lipgloss](https://github.com/charmbracelet/lipgloss). 7 views, 10 structured visualizers, ~9,800 lines of Go.

```bash
# Build and run
cd tui
go build -o agent-tui .
./agent-tui
```

The TUI automatically starts the reasoning server on launch. Requires Go 1.18+.

#### Chat View

The default view. Split-pane layout with a 16-agent sidebar, chat panel with live streaming, and a metrics bar showing TTFT, tokens/sec, and token count in real-time.

![Chat View](assets/tui-chat.svg)

Press `v` to toggle **structured visualization mode**. Instead of raw text, you see the agent's reasoning process rendered live: tree diagrams for ToT, swimlanes for ReAct, vote tallies for Consistency, score gauges for Refinement, and more.

Press `p` to open the **hyperparameter tuner**. Adjust ToT width/depth, Consistency samples, Refinement score thresholds, and other agent parameters before running a query.

Press `?` to invoke the **strategy advisor**. The MetaReasoningAgent analyzes your query and recommends the best strategy.

#### Arena Mode

All 16 agents race simultaneously on the same query. 4x4 grid with live streaming per cell. A leaderboard bar updates as agents finish.

![Arena Mode](assets/tui-arena.svg)

After all agents finish, press `Enter` for a summary table ranked by completion time, tokens, and TPS. Press `s` to save the full arena report.

#### Head-to-Head Duel

Pick any two agents, same query, side-by-side streaming. Live metrics comparison at the bottom. Press `j` after both finish to invoke an LLM judge that scores both responses.

![Duel Mode](assets/tui-duel.svg)

#### Step-Through Debugger

Pause an agent between LLM calls. Inspect intermediate state (tree nodes, scores, prompts, raw responses). Step forward one call at a time or let it run to completion.

![Debugger](assets/tui-debugger.svg)

#### Benchmark Dashboard

4-tab native dashboard reading existing JSON benchmark files:
- **Reasoning**: strategy x task heatmap
- **Accuracy**: bar charts by dataset (GSM8K, MMLU, ARC, HellaSwag)
- **Speed**: TPS bars and latency columns per model
- **Compare**: OCI vs Ollama side-by-side with color-coded winners

#### Session Browser

Browse, search, and re-run past conversations. Filter by type (chat/arena/duel), strategy, or free text. Export to markdown. Every interaction auto-saves to `data/sessions/`.

#### Agent Guide

Reference cards for all 16 agents: how it works, best for, parameters, trade-offs, and research reference. Press `Enter` on any card to jump straight into a chat with that agent.

#### TUI Configuration

Optional YAML config at `~/.config/agent-reasoning/config.yaml`:

```yaml
server:
  port: 8080
  auto_start: true
ollama:
  url: http://localhost:11434
defaults:
  model: qwen3.5:9b
  visualization: true    # structured viz on by default
ui:
  sidebar_width: 22
  metrics_bar: true
sessions:
  auto_save: true
  directory: data/sessions
```

If the file doesn't exist, sane defaults are used. The file is never auto-created.

#### TUI Keybindings

| Key | Context | Action |
|-----|---------|--------|
| `j/k` or `↑/↓` | Sidebar, lists | Navigate |
| `Tab` | Any view | Switch focus (sidebar / input) |
| `Enter` | Sidebar | Select agent or action |
| `Enter` | Input | Submit query |
| `Esc` | Streaming | Cancel current stream |
| `Esc` | Any view | Return to chat |
| `v` | Chat | Toggle structured visualization |
| `p` | Chat | Open hyperparameter tuner |
| `?` | Chat (with text) | Strategy advisor |
| `D` | Chat | Debug last query |
| `S` | Any view | Jump to sessions |
| `1-4` | Benchmarks | Switch tab |
| `h/l` | Benchmarks | Navigate tabs |
| `n` | Debugger | Step forward |
| `c` | Debugger | Continue (run to end) |
| `b` | Debugger | Step backward (replay) |
| `i` | Debugger | Toggle inspector mode |
| `j` | Duel (finished) | Invoke LLM judge |
| `s` | Arena (finished) | Save report |
| `q` or `Ctrl+C` | Not streaming | Quit |

#### TUI Views Summary

| View | Access | Description |
|------|--------|-------------|
| Chat | Default | Single-agent conversation with structured visualization |
| Arena | Sidebar: "Arena Mode" | 16 agents racing on same query, live 4x4 grid |
| Duel | Sidebar: "Head-to-Head" | Two agents side-by-side with LLM judge |
| Debugger | Sidebar: "Debugger" or `D` | Step-through reasoning with state inspection |
| Benchmarks | Sidebar: "Benchmarks" | 4-tab dashboard with terminal charts |
| Sessions | Sidebar: "Sessions" | Browse, search, re-run, export past chats |
| Agent Guide | Sidebar: "Agent Guide" | Reference cards for all 16 strategies |

### 3. Python API (For Developers)
Use the `ReasoningInterceptor` as a drop-in replacement for your LLM client.

```python
from agent_reasoning import ReasoningInterceptor

client = ReasoningInterceptor()

# Append the strategy to the model name with a '+'
response = client.generate(
    model="gemma3:270m+tot",
    prompt="I have a 3-gallon and 5-gallon jug. How do I measure 4 gallons?"
)
print(response["response"])
```

**Using agents directly:**

```python
from agent_reasoning.agents import CoTAgent, ToTAgent, ReActAgent

# Create an agent
agent = CoTAgent(model="gemma3:270m")

# Stream responses
for chunk in agent.stream("Explain quantum entanglement step by step"):
    print(chunk, end="")
```

**Using refinement agents for quality content:**

```python
from agent_reasoning.agents import RefinementLoopAgent, ComplexRefinementLoopAgent

# Refinement Loop: iteratively improves until score threshold met
agent = RefinementLoopAgent(model="gemma3:270m", score_threshold=0.9, max_iterations=5)
for chunk in agent.stream("Write a technical explanation of neural networks"):
    print(chunk, end="")

# Complex Pipeline: 5-stage optimization for production-quality content
agent = ComplexRefinementLoopAgent(model="gemma3:270m", score_threshold=0.85)
for chunk in agent.stream("Write a blog post about machine learning"):
    print(chunk, end="")
```

### 4. Reasoning Gateway Server
Run a proxy server that impersonates Ollama. This allows **any** Ollama-compatible app (LangChain, Web UIs) to gain reasoning capabilities without code changes.

```bash
# If installed via pip:
agent-reasoning-server --port 8080

# Or from source:
python server.py
```

Then configure your app:
*   **Base URL**: `http://localhost:8080`
*   **Model**: `gemma3:270m+cot` (or `+tot`, `+react`, etc.)

**API Endpoints:**
```bash
# Generate with reasoning strategy
curl http://localhost:8080/api/generate -d '{
  "model": "gemma3:270m+cot",
  "prompt": "Why is the sky blue?"
}'

# List available agents with descriptions
curl http://localhost:8080/api/agents

# List available model+strategy combinations
curl http://localhost:8080/api/tags
```

---

## 🧠 Architectures in Detail

| Architecture | Description | Best For | Papers |
|--------------|-------------|----------|--------|
| **Chain-of-Thought** | Step-by-step reasoning prompt injection. | Math, Logic, Explanations | [Wei et al. (2022)](https://arxiv.org/abs/2201.11903) |
| **Self-Reflection** | Draft -> Critique -> Refine loop. | Creative Writing, High Accuracy | [Shinn et al. (2023)](https://arxiv.org/abs/2303.11366) |
| **ReAct** | Interleaves Reasoning and Tool Usage. | Fact-checking, Calculations | [Yao et al. (2022)](https://arxiv.org/abs/2210.03629) |
| **Tree of Thoughts** | Explores multiple reasoning branches (BFS/DFS). | Complex Riddles, Strategy | [Yao et al. (2023)](https://arxiv.org/abs/2305.10601) |
| **Decomposed** | Breaks complex queries into sub-tasks. | Planning, Long-form answers | [Khot et al. (2022)](https://arxiv.org/abs/2210.02406) |
| **Recursive (RLM)** | Uses Python REPL to recursively process prompt variables. | Long-context processing | [Author et al. (2025)](https://arxiv.org/abs/2512.24601) |
| **Refinement Loop** | Generator → Critic (0.0-1.0 score) → Refiner iterative loop. | Technical Writing, Quality Content | Inspired by [Madaan et al. (2023)](https://arxiv.org/abs/2303.17651) |
| **Complex Refinement** | 5-stage pipeline: Accuracy → Clarity → Depth → Examples → Polish. | Long-form Articles, Documentation | Multi-stage refinement architecture |
| **Adversarial Debate** | Pro/con debate rounds with judge evaluation. | Controversial Topics, Analysis | [Irving et al. (2018)](https://arxiv.org/abs/1805.00899) |
| **MCTS** | Monte Carlo Tree Search with UCB1 selection. | Complex Strategy, Planning | [Browne et al. (2012)](https://doi.org/10.1109/TCIAIG.2012.2186810) |
| **Analogical** | Solve by finding and applying structural analogies. | Novel Problems, Cross-domain | [Gentner (1983)](https://doi.org/10.1111/j.1551-6708.1983.tb00497.x) |
| **Socratic** | Progressive questioning to deepen understanding. | Deep Understanding, Philosophy | [Paul & Elder (2007)](https://www.criticalthinking.org/) |
| **Meta-Reasoning** | Auto-classifies query and routes to optimal strategy. | Any Query Type (auto-selection) | Novel |

---

## 🎯 Accuracy Benchmarks

Evaluate reasoning strategies against standard NLP datasets to measure accuracy improvements from cognitive architectures. The benchmark system includes embedded question sets from 4 standard datasets.

| Dataset | Category | Questions | Format | Reference |
|---------|----------|-----------|--------|-----------|
| **GSM8K** | Math Reasoning | 30 | Open-ended number | Cobbe et al. (2021) |
| **MMLU** | Knowledge (57 subjects) | 30 | Multiple choice (A-D) | Hendrycks et al. (2021) |
| **ARC-Challenge** | Science Reasoning | 25 | Multiple choice (A-D) | Clark et al. (2018) |
| **HellaSwag** | Commonsense | 20 | Multiple choice (A-D) | Zellers et al. (2019) |

### Results: `qwen3.5:9b` (9.7B Q4_K_M)

Full eval across 13 strategies (4,200 evaluations, March 2026):

| Strategy | GSM8K | MMLU | ARC-C | **Avg** |
|----------|-------|------|-------|---------|
| **Chain of Thought** | 94.0% | 82.0% | 90.0% | **88.7%** |
| **Recursive** | 96.0% | 78.0% | 88.0% | **87.3%** |
| **Self-Consistency** | 92.0% | 80.0% | 88.0% | **86.7%** |
| **Tree of Thoughts** | 96.0% | 74.0% | 90.0% | **86.7%** |
| **Standard** (baseline) | 96.0% | 66.0% | 82.0% | **81.3%** |
| **Self-Reflection** | 96.0% | 60.0% | 86.0% | **80.7%** |
| **Refinement Loop** | 94.0% | 60.0% | 80.0% | **78.0%** |
| **Socratic** | 74.0% | 76.0% | 84.0% | **78.0%** |
| **Debate** | 60.0% | 72.0% | 86.0% | **72.7%** |
| **Decomposed** | 88.0% | 54.0% | 60.0% | **67.3%** |
| **ReAct** | 84.0% | 46.0% | 70.0% | **66.7%** |

**Key findings:**
- **CoT** achieves the highest average accuracy (88.7%), outperforming Standard on MMLU (+16%) and ARC-C (+8%)
- **Recursive** and **ToT** cluster close behind at 86.7-87.3%
- **Self-Consistency** matches ToT at 86.7% through majority voting reliability
- **Standard** generation scores 96.0% on GSM8K but drops on MMLU (66.0%), showing reasoning strategies help most on knowledge tasks

### Accuracy Heatmap

![Accuracy Heatmap](benchmarks/charts/accuracy_heatmap.png)

### Average Accuracy by Strategy

![Accuracy by Strategy](benchmarks/charts/accuracy_by_strategy.png)

### Running Accuracy Benchmarks

```bash
# Interactive (select datasets and strategies):
python agent_cli.py --accuracy

# Or from the benchmark menu:
python agent_cli.py --benchmark
# → Select "Accuracy Benchmark"
```

Charts are auto-generated after each run to `benchmarks/charts/`.

### Python API

```python
from src.benchmarks.accuracy import AccuracyBenchmarkRunner, DATASET_REGISTRY

runner = AccuracyBenchmarkRunner(model="qwen3.5:9b")

# Run all datasets with specific strategies
for result in runner.run_all_datasets(
    strategies=["standard", "cot", "tot", "decomposed"],
    max_questions_per_dataset=10,  # Quick eval
):
    print(f"{result.strategy}: {'✓' if result.correct else '✗'}")

# Generate reports
reports = runner.generate_reports()
for r in reports:
    print(f"{r.dataset} | {r.strategy} | {r.accuracy_pct:.1f}%")
```

---

## 📚 Appendix A: Extending the System

To add a new reasoning strategy (e.g., "Reviewer-Critic"), simply:

1.  Create a class in `src/agent_reasoning/agents/` inheriting from `BaseAgent`.
2.  Implement the `stream(self, query)` method.
3.  Register it in `AGENT_MAP` in `src/agent_reasoning/interceptor.py`.

```python
from agent_reasoning.agents.base import BaseAgent

class MyNewAgent(BaseAgent):
    def stream(self, query):
        yield "Thinking differently...\n"
        # ... your custom logic ...
        yield "Final Answer"
```

## 🔧 Appendix B: Troubleshooting

*   **Model Not Found**: Ensure you have pulled the base model (`ollama pull gemma3:270m`).
*   **Timeout / Slow**: ToT and Self-Reflection make multiple calls to the LLM. With larger models (Llama3 70b), this can take time.
*   **Hallucinations**: The default demo uses `gemma3:270m` which is extremely small and prone to logic errors. Switch to `gemma2:9b` or `llama3` for reliable results.

---

## 📊 Benchmark Report (Example Outputs)

Below are real outputs generated by the `main.py` benchmark using `gemma3:270m`. Note that while the small model strives to follow the reasoning structures, its logic limitations highlight the importance of using larger models (e.g., `llama3` or `gemma2:9b`) for production.

### 1. Philosophy (Self-Consistency)
*Generates multiple reasoning paths and votes for the best answer.*

**Query:** "What is the meaning of life? Answer with a mix of biological and philosophical perspectives."
```text
[ConsistencyAgent]: Processing query via Self-Consistency (k=3)...
  Sample 1: [Detailed biological perspective on propagation...]
  Sample 2: [Philosophical view on existentialism and purpose...]
  Sample 3: [Synthesis of both views...]
Majority Logic: [Aggregated Best Answer from Votes]
```

### 2. Logic (Tree of Thoughts)
*Explores multiple branches (BFS) to solve riddles.*

**Query:** "I have a 3-gallon jug and a 5-gallon jug. How can I measure exactly 4 gallons of water?"
```text
[ToTAgent]: Processing query via Tree of Thoughts (BFS)...
Thinking via Tree of Thoughts (Depth=3, Width=2)...

[Step 1/3 - Exploring branches]
  Path Score: 0.0
  Path Score: 1.0

[Step 2/3 - Exploring branches]
  Path Score: 1.0
  Path Score: 1.0
  Path Score: 0.1

[Step 3/3 - Exploring branches]
  Path Score: 1.0 (Found solution state)

[Best Logic Trace selected. Generating Final Answer]
**Final Answer:**
1. Pour water from the 5-gallon jug into the 3-gallon jug.
2. You now have 2 gallons left in the 5-gallon jug.
3. Empty the 3-gallon jug.
4. Pour the 2 gallons from the 5-gallon jug into the 3-gallon jug.
5. Fill the 5-gallon jug again.
6. Pour from the 5-gallon jug into the 3-gallon jug until full (needs 1 gallon).
7. You are left with exactly 4 gallons in the 5-gallon jug.
```

### 3. Planning (Decomposed Agent)
*Breaks down complex tasks into sub-problems.*

**Query:** "Plan a detailed 3-day itinerary for Tokyo for a history buff who loves samurais and tea."
```text
[DecomposedAgent]: Decomposing the problem...

Sub-tasks Plan:
1.  **Define the Scope:** What historical period and specific area of Tokyo will the itinerary cover?
2.  **Identify Key Historical Sites:** What historical sites will the itinerary focus on?
3.  **Determine Traveler's Interests:** What types of historical sites will the itinerary include?
4.  **Outline the Itinerary:** What activities and attractions will be included in each day?
5.  **Estimate Duration:** How long will the itinerary last?

[DecomposedAgent]: Solving sub-task: 1. Define the Scope...
[DecomposedAgent]: Solving sub-task: 2. Identify Key Historical Sites...
...
Final Answer: [Detailed 3-day plan covering Meiji Shrine, Tea Ceremonies, and Samurai Museum]
```

### 4. Tool Use (ReAct Agent)
*Interleaves thought, action, and observation to solve problems.*

**Query:** "Who is the current CEO of Google? Calculate the square root of 144."
```text
[ReActAgent]: Processing query with ReAct...

--- Step 1 ---
Agent: Action: web_search[current CEO of Google]
Observation: Sundar Pichai is the current CEO of Google.
Final Answer: Sundar Pichai

Running web_search...
Observation: [1] Sundar Pichai - Wikipedia: ... He is the chief executive officer (CEO) of Alphabet Inc. and its subsidiary Google.
```

---

## 📊 Appendix C: Benchmark Charts

Benchmark charts are auto-generated after every benchmark run. Below are sample outputs using `qwen3.5:9b`.

### Response Latency by Strategy

Each reasoning strategy has different latency characteristics based on its internal architecture (multi-call agents like Refinement and Decomposed take longer; single-pass agents like CoT are faster).

![Latency](benchmarks/charts/benchmark_latency.png)

### Throughput (Tokens/Second)

Raw throughput comparison showing how many tokens each strategy produces per second of wall-clock time.

![Throughput](benchmarks/charts/benchmark_tps.png)

### TTFT vs Total Latency

Scatter plot showing the relationship between time-to-first-token and total response time. Points closer to the bottom-left are faster overall.

![Scatter](benchmarks/charts/benchmark_scatter.png)

### Strategy Comparison Summary

Side-by-side comparison of average latency, throughput, and TTFT across all tested strategies.

![Summary](benchmarks/charts/benchmark_summary.png)

### Performance Heatmap

Normalized heatmap where green = better performance. Latency and TTFT are inverted (lower is better). Useful for quick strategy selection.

![Heatmap](benchmarks/charts/benchmark_heatmap.png)

> Charts generated with `python agent_cli.py --benchmark`. Output saved to `benchmarks/charts/`.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">
  <a href="https://github.com/jasperan"><img src="https://img.shields.io/badge/GitHub-jasperan-181717?style=for-the-badge&logo=github" alt="GitHub"/></a>
  &nbsp;
  <a href="https://linkedin.com/in/jasperan"><img src="https://img.shields.io/badge/LinkedIn-jasperan-0A66C2?style=for-the-badge&logo=linkedin" alt="LinkedIn"/></a>
</div>
