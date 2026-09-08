#!/usr/bin/env python3
"""
Unified Benchmark Runner for Ollama vs OCI GenAI

Runs benchmarks on both local Ollama models and OCI cloud models,
then generates a comparison report.

Configuration is loaded from benchmarks/config.json
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Get the benchmarks directory
BENCHMARKS_DIR = Path(__file__).parent
CONFIG_PATH = BENCHMARKS_DIR / "config.json"


def load_config():
    """Load benchmark configuration."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    print(f"Error: Config file not found at {CONFIG_PATH}")
    sys.exit(1)


def run_ollama_benchmark(config, args):
    """Run Ollama benchmark."""
    ollama_models = [m["key"] for m in config.get("models", {}).get("ollama", [])]

    if not ollama_models:
        print("No Ollama models configured in config.json")
        return None

    if args.skip_ollama:
        print("Skipping Ollama benchmark (--skip-ollama)")
        return None

    output_file = BENCHMARKS_DIR / "ollama_results.json"

    cmd = [
        sys.executable,
        str(BENCHMARKS_DIR / "benchmark_ollama.py"),
        "--models",
        *ollama_models,
        "--iterations",
        str(args.iterations),
        "--output",
        str(output_file),
    ]

    if args.dry_run:
        cmd.append("--dry-run")

    print("\n" + "=" * 80)
    print("OLLAMA BENCHMARK")
    print("=" * 80)
    print(f"Models: {', '.join(ollama_models)}")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=BENCHMARKS_DIR)

    if result.returncode != 0:
        print(f"Ollama benchmark failed with code {result.returncode}")
        return None

    return output_file


def run_oci_benchmark(config, args):
    """Run OCI benchmark."""
    oci_config = config.get("oci", {})
    oci_models = [m["key"] for m in config.get("models", {}).get("oci", [])]

    if not oci_models:
        print("No OCI models configured in config.json")
        return None

    if args.skip_oci:
        print("Skipping OCI benchmark (--skip-oci)")
        return None

    # Set environment for OCI profile
    env = os.environ.copy()
    env["OCI_CLI_PROFILE"] = oci_config.get("profile", "DEFAULT")

    output_file = BENCHMARKS_DIR / "oci_results.json"

    cmd = [
        sys.executable,
        str(BENCHMARKS_DIR / "benchmark_oci.py"),
        "--profile",
        oci_config.get("profile", "DEFAULT"),
        "--models",
        *oci_models,
        "--iterations",
        str(args.iterations),
        "--output",
        str(output_file),
    ]

    if oci_config.get("compartment_id"):
        cmd.extend(["--compartment-id", oci_config.get("compartment_id")])

    if oci_config.get("endpoint"):
        cmd.extend(["--endpoint", oci_config.get("endpoint")])

    if args.dry_run:
        cmd.append("--dry-run")
    if args.parallel:
        cmd.append("--parallel")

    print("\n" + "=" * 80)
    print("OCI GENAI BENCHMARK")
    print("=" * 80)
    print(f"Profile: {oci_config.get('profile', 'DEFAULT')}")
    print(f"Compartment: {oci_config.get('compartment_id', 'N/A')[:50]}...")
    print(f"Endpoint: {oci_config.get('endpoint', 'N/A')}")
    print(f"Models: {', '.join(oci_models)}")
    print()

    result = subprocess.run(cmd, cwd=BENCHMARKS_DIR, env=env)

    if result.returncode != 0:
        print(f"OCI benchmark failed with code {result.returncode}")
        return None

    return output_file


def run_comparison(ollama_file, oci_file):
    """Run comparison between results."""
    cmd = [
        sys.executable,
        str(BENCHMARKS_DIR / "compare_results.py"),
    ]

    if ollama_file:
        cmd.extend(["--ollama-results", str(ollama_file)])
    if oci_file:
        cmd.extend(["--oci-results", str(oci_file)])

    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)

    subprocess.run(cmd, cwd=BENCHMARKS_DIR)


def main():
    config = load_config()
    default_iterations = config.get("defaults", {}).get("iterations", 3)

    parser = argparse.ArgumentParser(
        description="Run unified Ollama vs OCI GenAI benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full benchmark (both Ollama and OCI)
  python run_benchmark.py

  # Run with fewer iterations
  python run_benchmark.py --iterations 1

  # Skip Ollama, only run OCI
  python run_benchmark.py --skip-ollama

  # Skip OCI, only run Ollama
  python run_benchmark.py --skip-oci

  # Dry run (no API calls)
  python run_benchmark.py --dry-run

  # Just compare existing results
  python run_benchmark.py --compare-only
        """,
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=default_iterations,
        help=f"Number of iterations per prompt (default: {default_iterations})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate runs without API calls")
    parser.add_argument(
        "--parallel", action="store_true", help="Run OCI models in parallel for faster results"
    )
    parser.add_argument("--skip-ollama", action="store_true", help="Skip Ollama benchmark")
    parser.add_argument("--skip-oci", action="store_true", help="Skip OCI benchmark")
    parser.add_argument(
        "--compare-only", action="store_true", help="Only run comparison on existing results"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("UNIFIED BENCHMARK: Ollama (Local) vs OCI GenAI (Cloud)")
    print("=" * 80)
    print(f"Config: {CONFIG_PATH}")
    print(f"Iterations: {args.iterations}")
    print(f"Parallel OCI: {args.parallel}")
    print(f"Dry run: {args.dry_run}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    ollama_file = BENCHMARKS_DIR / "ollama_results.json"
    oci_file = BENCHMARKS_DIR / "oci_results.json"

    if not args.compare_only:
        # Run benchmarks
        ollama_result = run_ollama_benchmark(config, args)
        oci_result = run_oci_benchmark(config, args)

        if ollama_result:
            ollama_file = ollama_result
        if oci_result:
            oci_file = oci_result

    # Run comparison
    if ollama_file.exists() or oci_file.exists():
        run_comparison(
            ollama_file if ollama_file.exists() else None, oci_file if oci_file.exists() else None
        )
    else:
        print("\nNo results files found. Run benchmarks first.")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)
    print("Results saved to:")
    if ollama_file.exists():
        print(f"  - {ollama_file}")
    if oci_file.exists():
        print(f"  - {oci_file}")


if __name__ == "__main__":
    main()
