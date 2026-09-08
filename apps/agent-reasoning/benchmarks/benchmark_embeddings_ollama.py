import argparse
import json
import sys
import time

import requests


def benchmark_embeddings_ollama(model_name, text_input, dry_run=False):
    """
    Benchmarks embedding generation against a local Ollama instance.
    """
    if dry_run:
        return {
            "model": model_name,
            "input_len": len(text_input),
            "latency_ms": 45.0,  # Faster than generation
            "error": None,
        }

    url = "http://localhost:11434/api/embeddings"
    payload = {"model": model_name, "prompt": text_input}

    try:
        start_time = time.time()
        response = requests.post(url, json=payload)
        response.raise_for_status()
        end_time = time.time()

        total_latency = (end_time - start_time) * 1000

        return {
            "model": model_name,
            "input_len": len(text_input),
            "latency_ms": round(total_latency, 2),
            "error": None,
        }

    except Exception as e:
        return {"model": model_name, "input_len": len(text_input), "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Benchmark Ollama Embeddings")
    parser.add_argument(
        "--model", type=str, default="nomic-embed-text", help="Ollama embedding model tag"
    )
    parser.add_argument(
        "--input-file", type=str, default=None, help="JSON file containing list of text inputs"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="ollama_embeddings_results.json",
        help="Output file for results",
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate run without calling API")
    parser.add_argument(
        "--iterations", type=int, default=10, help="Number of iterations per text input"
    )

    args = parser.parse_args()

    # Default inputs if no file provided
    inputs = [
        "The quick brown fox jumps over the lazy dog.",
        "Artificial intelligence is transforming the world.",
        "Detailed benchmarks are crucial for performance analysis.",
    ]

    if args.input_file:
        try:
            with open(args.input_file, "r") as f:
                inputs = json.load(f)
        except FileNotFoundError:
            print(f"Error: Input file '{args.input_file}' not found.")
            sys.exit(1)

    results = []
    print(f"Starting embedding benchmark for Ollama model: {args.model}")
    print(f"Iterations per input: {args.iterations}")
    print(f"Dry run: {args.dry_run}")

    start_global = time.time()
    total_requests = len(inputs) * args.iterations
    completed = 0

    for i in range(args.iterations):
        for text in inputs:
            completed += 1
            print(f"[{completed}/{total_requests}] Iteration {i + 1}: input='{text[:30]}...'")

            res = benchmark_embeddings_ollama(args.model, text, args.dry_run)
            res["iteration"] = i + 1
            res["input_sample"] = text[:50]
            results.append(res)

            if res.get("error"):
                print(f"  Error: {res['error']}")
            else:
                print(f"  Latency: {res['latency_ms']}ms")

    total_time = time.time() - start_global
    print(f"\nBenchmark finished in {total_time:.2f}s")

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
