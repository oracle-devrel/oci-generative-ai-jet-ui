#!/usr/bin/env python3
"""
Expanded Accuracy Benchmark Runner

Runs accuracy benchmarks against HuggingFace datasets (not hardcoded questions)
for statistically significant results with full verifiability metadata.

Usage:
    python benchmarks/run_accuracy.py                          # defaults: qwen3.5:9b, 100 samples, all strategies
    python benchmarks/run_accuracy.py --model gemma3:latest    # different model
    python benchmarks/run_accuracy.py --samples 50             # fewer samples (faster)
    python benchmarks/run_accuracy.py --source embedded        # use hardcoded questions
    python benchmarks/run_accuracy.py --strategies cot,tot     # specific strategies only
    python benchmarks/run_accuracy.py --datasets gsm8k,mmlu    # specific datasets only
    python benchmarks/run_accuracy.py --quick                  # embedded questions, core strategies only
"""

import argparse
import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.benchmarks.accuracy import (
    DATASET_REGISTRY,
    AccuracyBenchmarkRunner,
    generate_accuracy_charts,
    get_model_fingerprint,
)

# Strategy tiers by speed (LLM calls per question)
FAST_STRATEGIES = ["standard", "cot", "decomposed", "least_to_most", "recursive"]
MEDIUM_STRATEGIES = ["reflection", "consistency", "refinement", "react", "socratic", "analogy"]
SLOW_STRATEGIES = ["tot", "mcts", "debate", "complex_refinement"]
CORE_STRATEGIES = ["standard", "cot", "tot", "consistency", "react"]
ALL_STRATEGIES = FAST_STRATEGIES + MEDIUM_STRATEGIES + SLOW_STRATEGIES


def parse_args():
    p = argparse.ArgumentParser(description="Run accuracy benchmarks with HuggingFace datasets")
    p.add_argument("--model", default="qwen3.5:9b", help="Ollama model name (default: qwen3.5:9b)")
    p.add_argument(
        "--source",
        choices=["embedded", "huggingface"],
        default="huggingface",
        help="Question source (default: huggingface)",
    )
    p.add_argument(
        "--samples",
        type=int,
        default=100,
        help="Questions per dataset for HuggingFace source (default: 100)",
    )
    p.add_argument("--seed", type=int, default=42, help="Random seed for reproducible sampling")
    p.add_argument(
        "--strategies", type=str, default=None, help="Comma-separated strategy list (default: all)"
    )
    p.add_argument(
        "--datasets", type=str, default=None, help="Comma-separated dataset list (default: all)"
    )
    p.add_argument(
        "--quick", action="store_true", help="Quick mode: embedded questions, core strategies only"
    )
    p.add_argument("--output-dir", default=None, help="Output directory for results")
    p.add_argument("--no-charts", action="store_true", help="Skip chart generation")
    p.add_argument(
        "--no-think",
        action="store_true",
        help="Disable thinking mode (recommended for qwen3.5 models)",
    )
    return p.parse_args()


def main():
    args = parse_args()

    if args.quick:
        args.source = "embedded"
        strategies = CORE_STRATEGIES
    elif args.strategies:
        strategies = [s.strip() for s in args.strategies.split(",")]
    else:
        strategies = ALL_STRATEGIES

    datasets = None
    if args.datasets:
        datasets = [d.strip() for d in args.datasets.split(",")]

    # Output directory
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or os.path.join(os.path.dirname(__file__), "results", ts)
    os.makedirs(out_dir, exist_ok=True)

    # Print config
    model_info = get_model_fingerprint(args.model)
    print("=" * 70)
    print("ACCURACY BENCHMARK")
    print("=" * 70)
    print(f"  Model:      {args.model}")
    print(f"  Digest:     {model_info.get('digest', 'N/A')[:24]}...")
    print(f"  Params:     {model_info.get('parameter_size', 'N/A')}")
    print(f"  Quant:      {model_info.get('quantization', 'N/A')}")
    print(f"  Source:     {args.source}")
    if args.source == "huggingface":
        print(f"  Samples:    {args.samples} per dataset")
        print(f"  Seed:       {args.seed}")
    print(f"  Strategies: {', '.join(strategies)}")
    print(f"  Datasets:   {', '.join(datasets or DATASET_REGISTRY.keys())}")
    think_val = False if args.no_think else None
    if args.no_think:
        print("  Think:      disabled")
    print(f"  Output:     {out_dir}")
    print("=" * 70)

    # Initialize runner
    runner = AccuracyBenchmarkRunner(
        model=args.model,
        source=args.source,
        samples=args.samples,
        seed=args.seed,
        think=think_val,
    )

    # Progress tracking
    total_done = 0
    total_correct = 0
    current_strategy = ""
    current_dataset = ""
    start_time = time.time()

    def on_start(q, strategy):
        nonlocal current_strategy, current_dataset
        if strategy != current_strategy or q.dataset != current_dataset:
            current_strategy = strategy
            current_dataset = q.dataset
            ds_name = DATASET_REGISTRY.get(q.dataset, {}).get("name", q.dataset)
            print(f"\n  [{ds_name}] {strategy}:", end="", flush=True)

    def on_done(result):
        nonlocal total_done, total_correct
        total_done += 1
        if result.correct:
            total_correct += 1
        marker = "." if result.correct else "X"
        print(marker, end="", flush=True)

        # Save incremental results every 50 questions
        if total_done % 50 == 0:
            runner.save_results(os.path.join(out_dir, "results_incremental.json"))

    # Run benchmarks
    target_datasets = datasets or list(DATASET_REGISTRY.keys())
    print("\nRunning benchmarks...")

    for dataset_id in target_datasets:
        if dataset_id not in DATASET_REGISTRY:
            print(f"\n  WARNING: Unknown dataset '{dataset_id}', skipping")
            continue

        for _ in runner.run_dataset(
            dataset_id,
            strategies,
            on_question_start=on_start,
            on_question_done=on_done,
        ):
            pass

    elapsed = time.time() - start_time

    # Final save
    results_path = os.path.join(out_dir, f"accuracy_{ts}.json")
    runner.save_results(results_path)

    # Generate reports
    reports = runner.generate_reports()

    # Print summary table
    print("\n\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Total evaluations: {total_done}")
    print(
        f"  Overall accuracy:  {total_correct}/{total_done} ({total_correct / total_done * 100:.1f}%)"
        if total_done
        else ""
    )
    print(f"  Wall time:         {elapsed / 60:.1f} min")
    print(f"  Avg per eval:      {elapsed / total_done:.1f}s" if total_done else "")
    print()

    # Pivot table: strategies × datasets
    from src.benchmarks.accuracy import compute_confidence_interval

    ds_ids = sorted(set(r.dataset for r in reports))
    strat_ids = sorted(set(r.strategy for r in reports))
    lookup = {(r.dataset, r.strategy): r for r in reports}

    # Header
    ds_names = {did: DATASET_REGISTRY.get(did, {}).get("name", did) for did in ds_ids}
    header = f"  {'Strategy':<20}"
    for did in ds_ids:
        header += f" {ds_names[did]:>12}"
    header += f" {'Avg':>8}"
    print(header)
    print("  " + "-" * (20 + 13 * len(ds_ids) + 9))

    for strat in strat_ids:
        row = f"  {strat:<20}"
        accs = []
        for did in ds_ids:
            r = lookup.get((did, strat))
            if r:
                ci_lo, ci_hi = compute_confidence_interval(r.correct, r.total)
                row += f" {r.accuracy_pct:>5.1f}% ±{(ci_hi - ci_lo) / 2:>3.0f}%"
                accs.append(r.accuracy_pct)
            else:
                row += f" {'—':>12}"
        avg = sum(accs) / len(accs) if accs else 0
        row += f" {avg:>6.1f}%"
        print(row)

    print()
    print(f"  Results saved: {results_path}")

    # Save TSV summary
    tsv_path = os.path.join(out_dir, f"accuracy_summary_{ts}.tsv")
    with open(tsv_path, "w") as f:
        f.write(
            "dataset\tstrategy\tcorrect\ttotal\taccuracy_pct\tci_95_low\tci_95_high\tavg_latency_ms\n"
        )
        for r in reports:
            ci_lo, ci_hi = compute_confidence_interval(r.correct, r.total)
            f.write(
                f"{r.dataset}\t{r.strategy}\t{r.correct}\t{r.total}\t{r.accuracy_pct}\t{ci_lo}\t{ci_hi}\t{r.avg_latency_ms}\n"
            )
    print(f"  Summary TSV:   {tsv_path}")

    # Generate charts
    if not args.no_charts and reports:
        charts_dir = os.path.join(out_dir, "charts")
        print(f"\n  Generating charts in {charts_dir}...")
        try:
            chart_files = generate_accuracy_charts(reports, args.model, charts_dir)
            for cf in chart_files:
                print(f"    -> {os.path.basename(cf)}")
        except Exception as e:
            print(f"    Chart generation failed: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
