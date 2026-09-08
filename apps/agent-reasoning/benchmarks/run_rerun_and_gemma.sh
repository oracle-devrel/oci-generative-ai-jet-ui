#!/bin/bash
# Re-run failed qwen3.5:9b strategies, then run all strategies on gemma3:latest.
# Combines all results and generates charts.
set -e
cd "$(dirname "$0")/.."

SAMPLES=50
SEED=42
BASE_DIR="benchmarks/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Failed strategies from the first run (Ollama crashed mid-reflection)
FAILED="reflection,consistency,refinement,react,tot,debate,socratic,analogy"
ALL="standard,cot,decomposed,least_to_most,recursive,reflection,consistency,refinement,react,tot,debate,socratic,analogy"

echo "========================================"
echo "BENCHMARK RE-RUN + GEMMA3"
echo "  Started: $(date)"
echo "========================================"

# ── Phase 1: Re-run failed qwen3.5:9b strategies ──
echo ""
echo ">>> PHASE 1: Re-running failed qwen3.5:9b strategies"
echo "    Strategies: $FAILED"

# Ensure Ollama is alive
sudo systemctl restart ollama
sleep 5

python3 benchmarks/run_accuracy.py \
  --model qwen3.5:9b \
  --source huggingface \
  --samples $SAMPLES \
  --seed $SEED \
  --strategies "$FAILED" \
  --no-think \
  --no-charts \
  --output-dir "$BASE_DIR/qwen_rerun_${TIMESTAMP}"

echo ""
echo ">>> Phase 1 complete at $(date)"

# ── Phase 2: Full gemma3:latest benchmark ──
echo ""
echo ">>> PHASE 2: Full gemma3:latest benchmark"
echo "    Strategies: $ALL"

# Restart Ollama fresh for gemma3
sudo systemctl restart ollama
sleep 5

python3 benchmarks/run_accuracy.py \
  --model gemma3:latest \
  --source huggingface \
  --samples $SAMPLES \
  --seed $SEED \
  --strategies "$ALL" \
  --no-charts \
  --output-dir "$BASE_DIR/gemma3_${TIMESTAMP}"

echo ""
echo ">>> Phase 2 complete at $(date)"

# ── Phase 3: Combine all results ──
echo ""
echo ">>> PHASE 3: Combining all results..."

python3 -c "
import json, glob, os, sys
sys.path.insert(0, '.')
from src.benchmarks.accuracy import generate_accuracy_charts, AccuracyReport, compute_confidence_interval
from collections import defaultdict

base = '$BASE_DIR'
ts = '$TIMESTAMP'
combined_dir = os.path.join(base, f'all_models_{ts}')
os.makedirs(combined_dir, exist_ok=True)

# Collect results per model
model_results = defaultdict(list)

# Qwen3.5:9b: valid tier1 + rerun
tier1_dir = os.path.join(base, 'combined_20260328_045902', 'tier1_fast')
rerun_dir = os.path.join(base, f'qwen_rerun_{ts}')
gemma_dir = os.path.join(base, f'gemma3_{ts}')

for src_dir, model_name in [(tier1_dir, 'qwen3.5:9b'), (rerun_dir, 'qwen3.5:9b'), (gemma_dir, 'gemma3:latest')]:
    for jf in glob.glob(os.path.join(src_dir, '*.json')):
        if 'incremental' in jf:
            continue
        with open(jf) as f:
            data = json.load(f)
        for r in data.get('results', []):
            # Skip error results from the crashed run
            if r.get('raw_response', '').startswith('Error: Could not reach'):
                continue
            model_results[model_name].append(r)

# Build reports per model
for model_name, results in model_results.items():
    groups = defaultdict(list)
    for r in results:
        groups[(r['dataset'], r['strategy'])].append(r)

    reports = []
    for (dataset, strategy), grp in sorted(groups.items()):
        total = len(grp)
        correct = sum(1 for r in grp if r['correct'])
        avg_lat = sum(r['latency_ms'] for r in grp) / total
        ci_lo, ci_hi = compute_confidence_interval(correct, total)
        reports.append({
            'dataset': dataset, 'strategy': strategy, 'model': model_name,
            'total': total, 'correct': correct,
            'accuracy_pct': round(correct / total * 100, 1),
            'avg_latency_ms': round(avg_lat, 2),
            'ci_95_low': ci_lo, 'ci_95_high': ci_hi,
        })

    # Save per-model JSON
    model_slug = model_name.replace(':', '_').replace('.', '_')
    out_path = os.path.join(combined_dir, f'accuracy_{model_slug}.json')
    with open(out_path, 'w') as f:
        json.dump({'model': model_name, 'results': results, 'reports': reports}, f, indent=2)

    # Generate per-model charts
    charts_dir = os.path.join(combined_dir, f'charts_{model_slug}')
    report_objs = [AccuracyReport(
        dataset=r['dataset'], strategy=r['strategy'], model=model_name,
        total=r['total'], correct=r['correct'],
        accuracy_pct=r['accuracy_pct'], avg_latency_ms=r['avg_latency_ms']
    ) for r in reports]
    try:
        chart_files = generate_accuracy_charts(report_objs, model_name, charts_dir)
        for cf in chart_files:
            print(f'  Chart ({model_name}): {os.path.basename(cf)}')
    except Exception as e:
        print(f'  Chart error ({model_name}): {e}')

    # Print summary table
    print(f'\n=== {model_name} ===')
    ds_ids = sorted(set(r['dataset'] for r in reports))
    strat_ids = sorted(set(r['strategy'] for r in reports))
    lookup = {(r['dataset'], r['strategy']): r for r in reports}

    header = f\"  {'Strategy':<20}\"
    for did in ds_ids:
        header += f' {did:>14}'
    header += f' {\"Avg\":>8}'
    print(header)
    print('  ' + '-' * (20 + 15 * len(ds_ids) + 9))

    for strat in strat_ids:
        row = f'  {strat:<20}'
        accs = []
        for did in ds_ids:
            r = lookup.get((did, strat))
            if r:
                row += f' {r[\"accuracy_pct\"]:>5.1f}% n={r[\"total\"]}'
                accs.append(r['accuracy_pct'])
            else:
                row += f' {\"—\":>14}'
        avg = sum(accs) / len(accs) if accs else 0
        row += f' {avg:>6.1f}%'
        print(row)

print(f'\nAll results saved to: {combined_dir}')
"

echo ""
echo "========================================"
echo "ALL BENCHMARKS COMPLETE"
echo "  Finished: $(date)"
echo "  Results:  $BASE_DIR/all_models_${TIMESTAMP}"
echo "========================================"
