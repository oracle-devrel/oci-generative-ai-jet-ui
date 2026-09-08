import argparse
import json
import random
import sys
import time

try:
    import oci
except ImportError:
    oci = None


def benchmark_embeddings_oci(compartment_id, endpoint, model_id, text_input, dry_run=False):
    """
    Benchmarks embedding generation against OCI GenAI Service.
    """
    if dry_run:
        return {
            "model": model_id,
            "input_len": len(text_input),
            "latency_ms": 120.0 + random.uniform(0, 20),
            "cost_estimate": 0.00001,
            "error": None,
        }

    if not oci:
        return {"error": "OCI SDK not installed. Run 'pip install oci'."}

    try:
        config = oci.config.from_file()
        gen_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
            config=config,
            service_endpoint=endpoint,
            retry_strategy=oci.retry.NoneRetryStrategy(),
            timeout=(10, 240),
        )

        embed_text_details = oci.generative_ai_inference.models.EmbedTextDetails(
            compartment_id=compartment_id,
            serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(model_id=model_id),
            inputs=[text_input],
            truncate="NONE",
        )

        start_time = time.time()
        gen_ai_inference_client.embed_text(embed_text_details)
        end_time = time.time()

        total_latency = (end_time - start_time) * 1000

        # Approximate cost calculation for embeddings
        cost_estimate = len(text_input) * 0.0000001

        return {
            "model": model_id,
            "input_len": len(text_input),
            "latency_ms": round(total_latency, 2),
            "cost_estimate": round(cost_estimate, 7),
            "error": None,
        }

    except Exception as e:
        return {"model": model_id, "input_len": len(text_input), "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Benchmark OCI GenAI Embeddings")
    parser.add_argument("--compartment-id", type=str, help="OCI Compartment ID")
    parser.add_argument(
        "--endpoint",
        type=str,
        default="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
        help="OCI GenAI Endpoint",
    )
    parser.add_argument(
        "--model-id",
        type=str,
        default="cohere.embed-v5.0",
        help="OCI Embedding Model ID (Embed 4/5)",
    )
    parser.add_argument(
        "--input-file", type=str, default=None, help="JSON file containing list of text inputs"
    )
    parser.add_argument(
        "--output", type=str, default="oci_embeddings_results.json", help="Output file for results"
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
    print(f"Starting embedding benchmark for OCI model: {args.model_id}")
    print(f"Iterations per input: {args.iterations}")
    print(f"Dry run: {args.dry_run}")

    start_global = time.time()
    total_requests = len(inputs) * args.iterations
    completed = 0

    for i in range(args.iterations):
        for text in inputs:
            completed += 1
            print(f"[{completed}/{total_requests}] Iteration {i + 1}: input='{text[:30]}...'")

            res = benchmark_embeddings_oci(
                args.compartment_id, args.endpoint, args.model_id, text, args.dry_run
            )
            res["iteration"] = i + 1
            res["input_sample"] = text[:50]
            results.append(res)

            if res.get("error"):
                print(f"  Error: {res['error']}")
            else:
                print(f"  Latency: {res['latency_ms']}ms, Cost: ${res['cost_estimate']}")

    total_time = time.time() - start_global
    print(f"\nBenchmark finished in {total_time:.2f}s")

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
