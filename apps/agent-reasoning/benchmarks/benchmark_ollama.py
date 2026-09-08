import argparse
import json
import sys
import time
from pathlib import Path

import requests

# Load config from benchmarks/config.json
CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    """Load benchmark configuration from config.json."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


CONFIG = load_config()


def benchmark_ollama(model_name, prompt, dry_run=False):
    """
    Benchmarks a single prompt against a local Ollama instance.
    """
    if dry_run:
        return {
            "model": model_name,
            "prompt_len": len(prompt),
            "ttft_ms": 150.5,
            "latency_ms": 1200.0,
            "output_tokens": 100,
            "tps": 83.3,
            "error": None,
        }

    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": True,  # Enable streaming to calculate TTFT
    }

    start_time = time.time()
    first_token_time = None
    response_text = ""
    token_count = 0

    try:
        with requests.post(url, json=payload, stream=True) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    decoded_line = json.loads(line.decode("utf-8"))
                    if not first_token_time:
                        first_token_time = time.time()

                    if not decoded_line.get("done"):
                        response_text += decoded_line.get("response", "")
                        token_count += 1

        end_time = time.time()

        ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
        total_latency = (end_time - start_time) * 1000
        tps = token_count / (total_latency / 1000) if total_latency > 0 else 0

        return {
            "model": model_name,
            "prompt_len": len(prompt),
            "ttft_ms": round(ttft, 2),
            "latency_ms": round(total_latency, 2),
            "output_tokens": token_count,
            "tps": round(tps, 2),
            "error": None,
        }

    except Exception as e:
        return {"model": model_name, "prompt_len": len(prompt), "error": str(e)}


def main():
    # Get defaults from config
    default_models = [m["key"] for m in CONFIG.get("models", {}).get("ollama", [{"key": "llama2"}])]
    default_iterations = CONFIG.get("defaults", {}).get("iterations", 3)
    default_prompts = CONFIG.get("defaults", {}).get(
        "prompts",
        [
            "Explain the concept of recursion in programming with a simple example.",
            "What are the key differences between SQL and NoSQL databases?",
            "Write a Python function to find the longest common subsequence of two strings.",
        ],
    )

    parser = argparse.ArgumentParser(description="Benchmark Ollama Local Inference")
    parser.add_argument(
        "--models",
        nargs="+",
        default=default_models,
        help="Ollama model tags to use (space separated)",
    )
    parser.add_argument(
        "--prompts-file", type=str, default=None, help="JSON file containing list of prompts"
    )
    parser.add_argument(
        "--output", type=str, default="ollama_results.json", help="Output file for results"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate run without calling API")
    parser.add_argument(
        "--iterations",
        type=int,
        default=default_iterations,
        help=f"Number of iterations per prompt (default: {default_iterations})",
    )

    args = parser.parse_args()

    # Default prompts from config
    prompts = default_prompts

    if args.prompts_file:
        try:
            with open(args.prompts_file, "r") as f:
                prompts = json.load(f)
        except FileNotFoundError:
            print(f"Error: Prompts file '{args.prompts_file}' not found.")
            sys.exit(1)

    results = []
    print(f"Starting benchmark for Ollama models: {args.models}")
    print(f"Iterations per prompt: {args.iterations}")
    print(f"Dry run: {args.dry_run}")

    start_global = time.time()

    total_requests = len(prompts) * args.iterations * len(args.models)
    completed = 0

    for model in args.models:
        print(f"\n--- Benchmarking Model: {model} ---")
        for i in range(args.iterations):
            for prompt in prompts:
                completed += 1
                print(
                    f"[{completed}/{total_requests}] Model={model}, Iteration {i + 1}: prompt='{prompt[:30]}...'"
                )

                res = benchmark_ollama(model, prompt, args.dry_run)
                res["iteration"] = i + 1
                res["prompt_sample"] = prompt[:50]
                results.append(res)

                if res.get("error"):
                    print(f"  Error: {res['error']}")
                else:
                    print(f"  TTFT: {res['ttft_ms']}ms, TPS: {res['tps']}")

    total_time = time.time() - start_global
    print(f"\nBenchmark finished in {total_time:.2f}s")

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
