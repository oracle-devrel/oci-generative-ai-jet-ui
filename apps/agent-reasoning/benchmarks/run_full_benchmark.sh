#!/bin/bash
# Full benchmark pipeline: runs all strategy tiers sequentially, then combines results and generates charts.
# Usage: nohup bash benchmarks/run_full_benchmark.sh > benchmarks/results/full_benchmark.log 2>&1 &

set -e
cd "$(dirname "$0")/.."

MODEL="qwen3.5:9b"
SAMPLES=50
SEED=42
BASE_DIR="benchmarks/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMBINED_DIR="$BASE_DIR/combined_${TIMESTAMP}"

mkdir -p "$COMBINED_DIR"

echo "========================================"
echo "FULL BENCHMARK PIPELINE"
echo "  Model:   $MODEL"
echo "  Samples: $SAMPLES per dataset"
echo "  Seed:    $SEED"
echo "  Output:  $COMBINED_DIR"
echo "  Started: $(date)"
echo "========================================"

# --- Tier 1: Fast strategies (1 LLM call per question) ---
echo ""
echo ">>> TIER 1: Fast strategies (standard, cot, decomposed, least_to_most, recursive)"
python3 benchmarks/run_accuracy.py \
  --model "$MODEL" \
  --source huggingface \
  --samples "$SAMPLES" \
  --seed "$SEED" \
  --strategies standard,cot,decomposed,least_to_most,recursive \
  --no-think \
  --no-charts \
  --output-dir "$COMBINED_DIR/tier1_fast"

echo ""
echo ">>> Tier 1 complete at $(date)"

# --- Tier 2: Medium strategies (3-5 LLM calls per question) ---
echo ""
echo ">>> TIER 2: Medium strategies (reflection, consistency, refinement, react)"
python3 benchmarks/run_accuracy.py \
  --model "$MODEL" \
  --source huggingface \
  --samples "$SAMPLES" \
  --seed "$SEED" \
  --strategies reflection,consistency,refinement,react \
  --no-think \
  --no-charts \
  --output-dir "$COMBINED_DIR/tier2_medium"

echo ""
echo ">>> Tier 2 complete at $(date)"

# --- Tier 3: Slow strategies (6+ LLM calls per question) ---
echo ""
echo ">>> TIER 3: Slow strategies (tot, debate)"
python3 benchmarks/run_accuracy.py \
  --model "$MODEL" \
  --source huggingface \
  --samples "$SAMPLES" \
  --seed "$SEED" \
  --strategies tot,debate \
  --no-think \
  --no-charts \
  --output-dir "$COMBINED_DIR/tier3_slow"

echo ""
echo ">>> Tier 3 complete at $(date)"

# --- Tier 4: Meta strategies ---
echo ""
echo ">>> TIER 4: Meta strategies (socratic, analogy)"
python3 benchmarks/run_accuracy.py \
  --model "$MODEL" \
  --source huggingface \
  --samples "$SAMPLES" \
  --seed "$SEED" \
  --strategies socratic,analogy \
  --no-think \
  --no-charts \
  --output-dir "$COMBINED_DIR/tier4_meta"

echo ""
echo ">>> Tier 4 complete at $(date)"

# --- Combine results ---
echo ""
echo ">>> Combining all tier results..."
python3 -c "
import json, glob, os, sys
sys.path.insert(0, '.')
from src.benchmarks.accuracy import generate_accuracy_charts, AccuracyReport, compute_confidence_interval

combined_dir = '$COMBINED_DIR'
all_results = []
all_reports = []
metadata = {}

for tier_dir in sorted(glob.glob(os.path.join(combined_dir, 'tier*'))):
    json_files = glob.glob(os.path.join(tier_dir, '*.json'))
    for jf in json_files:
        if 'incremental' in jf:
            continue
        with open(jf) as f:
            data = json.load(f)
        all_results.extend(data.get('results', []))
        all_reports.extend(data.get('reports', []))
        if not metadata:
            metadata = {k: v for k, v in data.items() if k not in ('results', 'reports')}

# Rebuild reports with CI from combined results
from collections import defaultdict
groups = defaultdict(list)
for r in all_results:
    groups[(r['dataset'], r['strategy'])].append(r)

final_reports = []
for (dataset, strategy), results in sorted(groups.items()):
    total = len(results)
    correct = sum(1 for r in results if r['correct'])
    avg_lat = sum(r['latency_ms'] for r in results) / total
    ci_lo, ci_hi = compute_confidence_interval(correct, total)
    final_reports.append({
        'dataset': dataset,
        'strategy': strategy,
        'model': metadata.get('model', 'unknown'),
        'total': total,
        'correct': correct,
        'accuracy_pct': round(correct / total * 100, 1),
        'avg_latency_ms': round(avg_lat, 2),
        'ci_95_low': ci_lo,
        'ci_95_high': ci_hi,
        'timestamp': metadata.get('timestamp', ''),
    })

# Save combined
combined_path = os.path.join(combined_dir, 'accuracy_combined.json')
combined_data = {**metadata, 'results': all_results, 'reports': final_reports}
with open(combined_path, 'w') as f:
    json.dump(combined_data, f, indent=2)
print(f'  Combined {len(all_results)} results -> {combined_path}')

# Generate charts
charts_dir = os.path.join(combined_dir, 'charts')
report_objs = [AccuracyReport(
    dataset=r['dataset'], strategy=r['strategy'], model=r.get('model',''),
    total=r['total'], correct=r['correct'],
    accuracy_pct=r['accuracy_pct'], avg_latency_ms=r['avg_latency_ms']
) for r in final_reports]
chart_files = generate_accuracy_charts(report_objs, metadata.get('model',''), charts_dir)
for cf in chart_files:
    print(f'  Chart: {os.path.basename(cf)}')

# Print summary table
print()
print('COMBINED RESULTS:')
ds_ids = sorted(set(r['dataset'] for r in final_reports))
strat_ids = sorted(set(r['strategy'] for r in final_reports))
lookup = {(r['dataset'], r['strategy']): r for r in final_reports}

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
"

echo ""
echo "========================================"
echo "FULL BENCHMARK COMPLETE"
echo "  Finished: $(date)"
echo "  Results:  $COMBINED_DIR"
echo "========================================"
