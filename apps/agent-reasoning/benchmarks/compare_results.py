#!/usr/bin/env python3
"""
Compare benchmark results between Ollama (local) and OCI GenAI (cloud).

Supports both old flat format and new format with metadata wrapper.
"""

import argparse
import json
import sys

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False


def load_results(filepath):
    """Load results from JSON file, handling both old and new formats."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Handle new format with metadata wrapper
        if isinstance(data, dict) and "results" in data:
            return data["results"], data.get("metadata", {})

        # Handle old flat list format
        if isinstance(data, list):
            return data, {}

        print(f"Warning: Unexpected format in {filepath}")
        return [], {}

    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        return None, None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        return None, None


def calc_metrics(data):
    """Calculate average metrics from a list of benchmark results."""
    valid_latency = [d["latency_ms"] for d in data if not d.get("error") and d.get("latency_ms")]
    valid_ttft = [d["ttft_ms"] for d in data if not d.get("error") and d.get("ttft_ms")]
    valid_tps = [d["tps"] for d in data if not d.get("error") and d.get("tps")]
    valid_cost = [d["cost_estimate"] for d in data if not d.get("error") and d.get("cost_estimate")]
    valid_tokens = [d["output_tokens"] for d in data if not d.get("error") and d.get("output_tokens")]

    return {
        "avg_latency": sum(valid_latency) / len(valid_latency) if valid_latency else 0,
        "avg_ttft": sum(valid_ttft) / len(valid_ttft) if valid_ttft else 0,
        "avg_tps": sum(valid_tps) / len(valid_tps) if valid_tps else 0,
        "avg_cost": sum(valid_cost) / len(valid_cost) if valid_cost else 0,
        "avg_tokens": sum(valid_tokens) / len(valid_tokens) if valid_tokens else 0,
        "success_count": len(valid_latency),
        "total_count": len(data),
    }


def group_by_model(data):
    """Group results by model name."""
    models = {}
    for entry in data:
        model = entry.get("model", "unknown")
        if model not in models:
            models[model] = []
        models[model].append(entry)
    return models


def print_simple_table(table, headers):
    """Print table without tabulate dependency."""
    # Calculate column widths
    widths = [max(len(str(row[i])) for row in [headers] + table) for i in range(len(headers))]

    # Print header
    header_line = " | ".join(f"{h:<{widths[i]}}" for i, h in enumerate(headers))
    separator = "-+-".join("-" * w for w in widths)
    print(header_line)
    print(separator)

    # Print rows
    for row in table:
        row_line = " | ".join(f"{str(cell):<{widths[i]}}" for i, cell in enumerate(row))
        print(row_line)


def compare_results(ollama_file, oci_file, show_all=False):
    """Compare Ollama and OCI benchmark results."""
    ollama_data, ollama_meta = load_results(ollama_file)
    oci_data, oci_meta = load_results(oci_file)

    if ollama_data is None and oci_data is None:
        print("Error: Could not load any results files.")
        sys.exit(1)

    # Initialize empty lists if file not found
    ollama_data = ollama_data or []
    oci_data = oci_data or []

    # Group by model
    ollama_models = group_by_model(ollama_data)
    oci_models = group_by_model(oci_data)

    headers = ["Source", "Model", "Provider", "Latency", "TTFT", "Tokens", "TPS", "Cost", "Success"]
    table = []

    # Process Ollama Models
    for model, entries in ollama_models.items():
        metrics = calc_metrics(entries)
        lat = f"{metrics['avg_latency']:.0f}ms" if metrics['avg_latency'] else "N/A"
        ttft = f"{metrics['avg_ttft']:.0f}ms" if metrics['avg_ttft'] else "N/A"
        tps = f"{metrics['avg_tps']:.1f}" if metrics['avg_tps'] else "N/A"
        tokens = f"{metrics['avg_tokens']:.0f}" if metrics['avg_tokens'] else "N/A"
        success = f"{metrics['success_count']}/{metrics['total_count']}"
        table.append(["Ollama", model, "local", lat, ttft, tokens, tps, "GPU", success])

    # Process OCI Models
    for model, entries in oci_models.items():
        metrics = calc_metrics(entries)

        # Get provider from first entry
        provider = entries[0].get("provider", "oci") if entries else "oci"

        lat = f"{metrics['avg_latency']:.0f}ms" if metrics['avg_latency'] else "N/A"
        ttft = f"{metrics['avg_ttft']:.0f}ms" if metrics['avg_ttft'] else "N/A"
        tokens = f"{metrics['avg_tokens']:.0f}" if metrics['avg_tokens'] else "N/A"

        # Calculate TPS from tokens and latency if not directly available
        if metrics['avg_tps']:
            tps = f"{metrics['avg_tps']:.1f}"
        elif metrics['avg_tokens'] and metrics['avg_latency']:
            tps_calc = metrics['avg_tokens'] / (metrics['avg_latency'] / 1000)
            tps = f"{tps_calc:.1f}"
        else:
            tps = "N/A"

        cost = f"${metrics['avg_cost']:.5f}" if metrics['avg_cost'] else "N/A"
        success = f"{metrics['success_count']}/{metrics['total_count']}"

        table.append(["OCI", model, provider, lat, ttft, tokens, tps, cost, success])

    # Sort table by latency (fastest first)
    def sort_key(row):
        lat_str = row[3]
        if lat_str == "N/A":
            return float('inf')
        return float(lat_str.replace('ms', ''))

    table.sort(key=sort_key)

    # Print results
    print("\n" + "=" * 100)
    print("BENCHMARK COMPARISON: Ollama (Local) vs OCI GenAI (Cloud)")
    print("=" * 100)

    if ollama_meta:
        print(f"\nOllama: {len(ollama_models)} model(s), {len(ollama_data)} total runs")
    if oci_meta:
        endpoint = oci_meta.get("endpoint", "unknown")
        print(f"OCI: {len(oci_models)} model(s), {len(oci_data)} total runs")
        print(f"     Endpoint: {endpoint}")

    print()

    if TABULATE_AVAILABLE:
        print(tabulate(table, headers=headers, tablefmt="github"))
    else:
        print_simple_table(table, headers)

    print()

    # Print insights
    all_models = {**{f"Ollama:{k}": v for k, v in ollama_models.items()},
                  **{f"OCI:{k}": v for k, v in oci_models.items()}}

    if all_models:
        print("-" * 110)
        print("INSIGHTS:")

        # Find fastest by latency
        fastest = min(
            ((m, calc_metrics(e)['avg_latency']) for m, e in all_models.items()
             if calc_metrics(e)['avg_latency'] > 0),
            key=lambda x: x[1],
            default=None
        )

        # Find best TTFT
        best_ttft = min(
            ((m, calc_metrics(e)['avg_ttft']) for m, e in all_models.items()
             if calc_metrics(e)['avg_ttft'] > 0),
            key=lambda x: x[1],
            default=None
        )

        # Find highest throughput
        highest_tps = max(
            ((m, calc_metrics(e)['avg_tps']) for m, e in all_models.items()
             if calc_metrics(e)['avg_tps'] > 0),
            key=lambda x: x[1],
            default=None
        )

        # Find most tokens generated
        most_tokens = max(
            ((m, calc_metrics(e)['avg_tokens']) for m, e in all_models.items()
             if calc_metrics(e)['avg_tokens'] > 0),
            key=lambda x: x[1],
            default=None
        )

        if fastest:
            print(f"  🏆 Fastest (Latency):    {fastest[0]} ({fastest[1]:.0f}ms)")
        if best_ttft:
            print(f"  ⚡ Best TTFT:            {best_ttft[0]} ({best_ttft[1]:.0f}ms)")
        if highest_tps:
            print(f"  🚀 Highest Throughput:  {highest_tps[0]} ({highest_tps[1]:.1f} tokens/s)")
        if most_tokens:
            print(f"  📝 Most Tokens:         {most_tokens[0]} ({most_tokens[1]:.0f} avg tokens)")

        # Cost comparison
        total_oci_cost = sum(
            calc_metrics(e)['avg_cost'] * calc_metrics(e)['total_count']
            for e in oci_models.values()
        )
        if total_oci_cost > 0:
            print(f"  💰 Total OCI Cost:      ${total_oci_cost:.4f}")

        print("-" * 110)


def main():
    parser = argparse.ArgumentParser(
        description="Compare Ollama and OCI GenAI benchmark results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python compare_results.py
  python compare_results.py --ollama-results my_ollama.json --oci-results my_oci.json
        """
    )
    parser.add_argument("--ollama-results", type=str, default="ollama_results.json",
                       help="Ollama results JSON file")
    parser.add_argument("--oci-results", type=str, default="oci_results.json",
                       help="OCI results JSON file")
    parser.add_argument("--all", action="store_true",
                       help="Show all metrics including failed runs")

    args = parser.parse_args()

    compare_results(args.ollama_results, args.oci_results, show_all=args.all)


if __name__ == "__main__":
    main()
