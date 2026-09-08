import argparse
import json
import sys

from tabulate import tabulate


def compare_embeddings(ollama_file, oci_file):
    try:
        with open(ollama_file, "r") as f:
            ollama_data = json.load(f)
        with open(oci_file, "r") as f:
            oci_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Error loading files: {e}")
        sys.exit(1)

    headers = ["Source", "Model", "Avg Latency (ms)", "Avg Cost ($/embedding)"]
    table = []

    def calc_metrics(data):
        valid_latency = [
            d["latency_ms"] for d in data if not d.get("error") and d.get("latency_ms")
        ]
        valid_cost = [d.get("cost_estimate", 0) for d in data if not d.get("error")]

        avg_lat = sum(valid_latency) / len(valid_latency) if valid_latency else 0
        avg_cost = sum(valid_cost) / len(valid_cost) if valid_cost else 0

        return avg_lat, avg_cost

    # Group and metrics for Ollama
    ollama_models = set(d.get("model") for d in ollama_data)
    for model in ollama_models:
        subset = [d for d in ollama_data if d.get("model") == model]
        lat, _ = calc_metrics(subset)
        table.append(["Ollama", model, f"{lat:.2f}", "GPU Rent"])

    # Group and metrics for OCI
    oci_models = set(d.get("model") for d in oci_data)
    for model in oci_models:
        subset = [d for d in oci_data if d.get("model") == model]
        lat, cost = calc_metrics(subset)
        table.append(["OCI GenAI", model, f"{lat:.2f}", f"${cost:.7f}"])

    print("\n--- Embedding Benchmark Comparison ---\n")
    print(tabulate(table, headers=headers, tablefmt="github"))
    print("\n")


def main():
    parser = argparse.ArgumentParser(description="Compare Embedding Results")
    parser.add_argument(
        "--ollama-results",
        type=str,
        default="ollama_embeddings_results.json",
        help="Ollama results JSON",
    )
    parser.add_argument(
        "--oci-results", type=str, default="oci_embeddings_results.json", help="OCI results JSON"
    )

    args = parser.parse_args()

    compare_embeddings(args.ollama_results, args.oci_results)


if __name__ == "__main__":
    main()
