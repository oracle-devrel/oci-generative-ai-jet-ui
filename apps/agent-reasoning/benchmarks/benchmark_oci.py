#!/usr/bin/env python3
"""
OCI Generative AI Benchmark Script

Benchmarks multiple OCI GenAI models including:
- OpenAI GPT-OSS-120B
- xAI Grok 4.1 Fast
- xAI Grok 3 Fast
- Meta Llama 4 Maverick
- Google Gemini 2.5 Pro
- Cohere Command models

Uses the Chat API with GenericChatRequest for non-Cohere models.
"""

import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

# Load config from benchmarks/config.json
CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    """Load benchmark configuration from config.json."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


CONFIG = load_config()

# Try to import oci, but allow running without it for dry-run
try:
    import oci
    from oci.generative_ai_inference import GenerativeAiInferenceClient
    from oci.generative_ai_inference.models import (
        ChatDetails,
        CohereChatRequest,
        GenericChatRequest,
        OnDemandServingMode,
        TextContent,
        UserMessage,
    )
    from oci.retry import NoneRetryStrategy

    OCI_AVAILABLE = True
except ImportError:
    OCI_AVAILABLE = False

# OCI Model Registry - Model IDs from Oracle documentation
# https://docs.oracle.com/en-us/iaas/Content/generative-ai/pretrained-models.htm
OCI_MODELS = {
    # OpenAI models
    "gpt-oss-120b": {
        "model_id": "openai.gpt-oss-120b",
        "display_name": "OpenAI GPT-OSS-120B",
        "provider": "openai",
        "type": "generic",
    },
    # xAI Grok models
    "grok-4.1-fast": {
        "model_id": "xai.grok-4-1-fast-non-reasoning",
        "display_name": "xAI Grok 4.1 Fast",
        "provider": "xai",
        "type": "generic",
    },
    "grok-3-fast": {
        "model_id": "xai.grok-3-fast",
        "display_name": "xAI Grok 3 Fast",
        "provider": "xai",
        "type": "generic",
    },
    # Meta Llama models
    "llama-4-maverick": {
        "model_id": "meta.llama-4-maverick-17b-128e-instruct-fp8",
        "display_name": "Meta Llama 4 Maverick",
        "provider": "meta",
        "type": "generic",
    },
    # Google Gemini models
    "gemini-2.5-pro": {
        "model_id": "google.gemini-2.5-pro",
        "display_name": "Google Gemini 2.5 Pro",
        "provider": "google",
        "type": "generic",
    },
    # Cohere models (for comparison)
    "cohere-command-r": {
        "model_id": "cohere.command-r-08-2024",
        "display_name": "Cohere Command R",
        "provider": "cohere",
        "type": "cohere",
    },
}

# Default models to benchmark
DEFAULT_MODELS = [
    "gpt-oss-120b",
    "grok-4.1-fast",
    "grok-3-fast",
    "llama-4-maverick",
    "gemini-2.5-pro",
]

# OCI Region endpoints
OCI_ENDPOINTS = {
    "us-chicago-1": "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
    "eu-frankfurt-1": "https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com",
    "uk-london-1": "https://inference.generativeai.uk-london-1.oci.oraclecloud.com",
    "ap-osaka-1": "https://inference.generativeai.ap-osaka-1.oci.oraclecloud.com",
}


def get_model_info(model_key: str) -> dict:
    """Get model info from registry or treat as raw model ID."""
    if model_key in OCI_MODELS:
        return OCI_MODELS[model_key]
    # Treat as raw OCI model ID
    return {
        "model_id": model_key,
        "display_name": model_key,
        "provider": "unknown",
        "type": "generic",  # Default to generic for unknown models
    }


def create_generic_chat_request(prompt: str, max_tokens: int = 1000, temperature: float = 0.7):
    """Create a GenericChatRequest for non-Cohere models.

    Note: Higher max_tokens needed for models like Gemini 2.5 Pro that use
    internal "thinking" tokens which count against the max_tokens limit.
    """
    return GenericChatRequest(
        api_format="GENERIC",
        messages=[UserMessage(content=[TextContent(text=prompt)])],
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=0.9,
    )


def create_cohere_chat_request(prompt: str, max_tokens: int = 1000, temperature: float = 0.7):
    """Create a CohereChatRequest for Cohere models."""
    return CohereChatRequest(
        message=prompt,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def benchmark_oci(
    compartment_id: str, endpoint: str, model_key: str, prompt: str, dry_run: bool = False
):
    """
    Benchmarks a single prompt against OCI Generative AI Service.

    Args:
        compartment_id: OCI Compartment OCID
        endpoint: OCI GenAI service endpoint
        model_key: Model key from OCI_MODELS or raw model ID
        prompt: The prompt to send
        dry_run: If True, simulate without API call

    Returns:
        dict with benchmark results
    """
    model_info = get_model_info(model_key)
    model_id = model_info["model_id"]

    if dry_run:
        # Simulate OCI performance per model provider
        base_latency = 350.0
        provider = model_info.get("provider", "unknown")

        if provider == "xai":
            base_latency = 280.0  # Grok models tend to be fast
        elif provider == "meta":
            base_latency = 320.0  # Llama models
        elif provider == "google":
            base_latency = 300.0  # Gemini models
        elif provider == "openai":
            base_latency = 450.0  # Larger model, slower
        elif provider == "cohere":
            base_latency = 350.0

        return {
            "model": model_key,
            "model_id": model_id,
            "display_name": model_info["display_name"],
            "provider": provider,
            "prompt_len": len(prompt),
            "ttft_ms": base_latency * 0.3 + random.uniform(0, 30),
            "latency_ms": base_latency + random.uniform(0, 80),
            "output_tokens": random.randint(80, 150),
            "cost_estimate": 0.00015 if provider != "openai" else 0.0003,
            "error": None,
        }

    if not OCI_AVAILABLE:
        return {
            "model": model_key,
            "model_id": model_id,
            "error": "OCI SDK not installed. Run 'pip install oci'.",
        }

    try:
        profile = os.environ.get("OCI_CLI_PROFILE", "DEFAULT")
        config = oci.config.from_file(profile_name=profile)
        oci.config.validate_config(config)

        # Fallback to config file values if arguments are missing
        final_compartment = compartment_id or config.get("compartment_id") or config.get("tenancy")
        final_endpoint = endpoint or config.get("endpoint")

        # If endpoint is still missing, try to resolve from region
        if not final_endpoint and config.get("region") and config.get("region") in OCI_ENDPOINTS:
            final_endpoint = OCI_ENDPOINTS[config.get("region")]

        if not final_compartment:
            return {
                "model": model_key,
                "model_id": model_id,
                "error": "No compartment_id provided and could not resolve from OCI config.",
            }

        genai_client = GenerativeAiInferenceClient(
            config=config,
            service_endpoint=final_endpoint,
            retry_strategy=NoneRetryStrategy(),
            timeout=(10, 240),
        )

        # Select appropriate chat request type based on model
        model_type = model_info.get("type", "generic")

        if model_type == "cohere":
            chat_request = create_cohere_chat_request(prompt)
        else:
            chat_request = create_generic_chat_request(prompt)

        chat_details = ChatDetails(
            compartment_id=final_compartment,
            serving_mode=OnDemandServingMode(model_id=model_id),
            chat_request=chat_request,
        )

        start_time = time.time()
        first_token_time = None

        # Make the API call
        response = genai_client.chat(chat_details)

        end_time = time.time()
        first_token_time = first_token_time or end_time  # Non-streaming fallback

        total_latency = (end_time - start_time) * 1000
        ttft = (first_token_time - start_time) * 1000 if first_token_time else total_latency

        # Extract response based on model type
        if model_type == "cohere":
            output_text = response.data.chat_response.text if response.data.chat_response else ""
        else:
            # GenericChatRequest response structure
            choices = response.data.chat_response.choices if response.data.chat_response else []
            if choices and len(choices) > 0:
                content = choices[0].message.content
                output_text = content[0].text if content else ""
            else:
                output_text = ""

        # Estimate tokens (rough approximation)
        output_tokens = int(len(output_text.split()) * 1.3)

        # Cost estimate (simplified - actual costs vary by model and region)
        input_tokens = len(prompt.split()) * 1.3
        cost_per_1k_input = 0.0015 if model_info["provider"] == "openai" else 0.0005
        cost_per_1k_output = 0.002 if model_info["provider"] == "openai" else 0.0015
        cost_estimate = (input_tokens / 1000 * cost_per_1k_input) + (
            output_tokens / 1000 * cost_per_1k_output
        )

        return {
            "model": model_key,
            "model_id": model_id,
            "display_name": model_info["display_name"],
            "provider": model_info["provider"],
            "prompt_len": len(prompt),
            "ttft_ms": round(ttft, 2),
            "latency_ms": round(total_latency, 2),
            "output_tokens": output_tokens,
            "output_preview": output_text[:100] + "..." if len(output_text) > 100 else output_text,
            "cost_estimate": round(cost_estimate, 6),
            "error": None,
        }

    except Exception as e:
        return {
            "model": model_key,
            "model_id": model_id,
            "display_name": model_info.get("display_name", model_key),
            "provider": model_info.get("provider", "unknown"),
            "prompt_len": len(prompt),
            "error": str(e),
        }


def print_model_registry():
    """Print available models in the registry."""
    print("\nAvailable OCI Models:")
    print("-" * 80)
    print(f"{'Key':<20} {'Display Name':<30} {'Provider':<10} {'Model ID'}")
    print("-" * 80)
    for key, info in OCI_MODELS.items():
        print(f"{key:<20} {info['display_name']:<30} {info['provider']:<10} {info['model_id']}")
    print("-" * 80)


def main():
    # Get defaults from config
    oci_config = CONFIG.get("oci", {})
    default_compartment = oci_config.get("compartment_id", None)
    default_endpoint = oci_config.get("endpoint", None)
    default_profile = oci_config.get("profile", "DEFAULT")
    default_iterations = CONFIG.get("defaults", {}).get("iterations", 3)

    parser = argparse.ArgumentParser(
        description="Benchmark OCI GenAI Service with multiple model providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Benchmark with saved config (uses config.json settings)
  python benchmark_oci.py

  # Benchmark specific models
  python benchmark_oci.py --models grok-4.1-fast gemini-2.5-pro

  # Override compartment ID
  python benchmark_oci.py --compartment-id ocid1.compartment...

  # Dry run to test without API calls
  python benchmark_oci.py --dry-run
        """,
    )
    parser.add_argument(
        "--compartment-id",
        type=str,
        default=default_compartment,
        help="OCI Compartment OCID (default: from config.json or OCI config)",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default=default_endpoint,
        help="OCI GenAI Endpoint (default: from config.json or OCI config)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=default_profile,
        help=f"OCI CLI profile name (default: {default_profile})",
    )
    parser.add_argument(
        "--region",
        type=str,
        choices=list(OCI_ENDPOINTS.keys()),
        help="OCI region (alternative to --endpoint)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Model keys or IDs to benchmark (space separated)",
    )
    parser.add_argument(
        "--prompts-file", type=str, default=None, help="JSON file containing list of prompts"
    )
    parser.add_argument(
        "--output", type=str, default="oci_results.json", help="Output file for results"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate run without calling API")
    parser.add_argument(
        "--iterations",
        type=int,
        default=default_iterations,
        help=f"Number of iterations per prompt (default: {default_iterations})",
    )
    parser.add_argument("--list-models", action="store_true", help="List available models and exit")
    parser.add_argument(
        "--parallel", action="store_true", help="Run all models in parallel for faster results"
    )
    parser.add_argument(
        "--workers", type=int, default=6, help="Number of parallel workers (default: 6)"
    )

    args = parser.parse_args()

    if args.list_models:
        print_model_registry()
        sys.exit(0)

    # Resolve OCI defaults from config file if not provided
    if OCI_AVAILABLE and (not args.compartment_id or not args.endpoint):
        try:
            config = oci.config.from_file(profile_name=args.profile)
            if not args.compartment_id:
                args.compartment_id = config.get("compartment_id") or config.get("tenancy")

            if not args.endpoint:
                args.endpoint = config.get("endpoint")
                if (
                    not args.endpoint
                    and config.get("region")
                    and config.get("region") in OCI_ENDPOINTS
                ):
                    args.endpoint = OCI_ENDPOINTS[config.get("region")]
        except Exception as e:
            if not args.dry_run:
                print(f"Warning: Failed to load OCI config to resolve defaults: {e}")

    # Set OCI profile in environment for the benchmark function
    os.environ["OCI_CLI_PROFILE"] = args.profile

    # Resolve endpoint from region if specified
    endpoint = args.endpoint
    if args.region:
        endpoint = OCI_ENDPOINTS.get(args.region, args.endpoint)

    # Validate compartment ID for non-dry-run
    if not args.dry_run and not args.compartment_id:
        print("Error: --compartment-id is required for live runs.")
        print("Configure it in benchmarks/config.json or pass --compartment-id")
        print("Use --dry-run to test without API calls, or --list-models to see available models.")
        sys.exit(1)

    # Default prompts from config or hardcoded fallback
    prompts = CONFIG.get("defaults", {}).get(
        "prompts",
        [
            "Explain the concept of recursion in programming with a simple example.",
            "What are the key differences between SQL and NoSQL databases?",
            "Write a Python function to find the longest common subsequence of two strings.",
        ],
    )

    if args.prompts_file:
        try:
            with open(args.prompts_file, "r") as f:
                prompts = json.load(f)
        except FileNotFoundError:
            print(f"Error: Prompts file '{args.prompts_file}' not found.")
            sys.exit(1)

    # Print configuration
    print("=" * 80)
    print("OCI Generative AI Benchmark")
    print("=" * 80)
    print(f"Endpoint: {endpoint}")
    print(f"Models: {', '.join(args.models)}")
    print(f"Prompts: {len(prompts)}")
    print(f"Iterations: {args.iterations}")
    print(f"Parallel: {args.parallel} (workers: {args.workers})")
    print(f"Dry run: {args.dry_run}")
    print("=" * 80)

    results = []
    start_global = time.time()
    total_requests = len(prompts) * args.iterations * len(args.models)

    if args.parallel:
        # Parallel execution
        print(f"\n🚀 Running {total_requests} requests in parallel with {args.workers} workers...")

        # Build list of all tasks
        tasks = []
        for model_key in args.models:
            for i in range(args.iterations):
                for prompt in prompts:
                    tasks.append(
                        {
                            "model_key": model_key,
                            "iteration": i + 1,
                            "prompt": prompt,
                        }
                    )

        # Thread-safe counter and lock for progress
        print_lock = Lock()
        completed = [0]  # Use list for mutable counter in closure

        def run_task(task):
            res = benchmark_oci(
                args.compartment_id, endpoint, task["model_key"], task["prompt"], args.dry_run
            )
            res["iteration"] = task["iteration"]
            res["prompt_sample"] = task["prompt"][:80]
            res["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            with print_lock:
                completed[0] += 1
                get_model_info(task["model_key"])
                if res.get("error"):
                    print(
                        f"[{completed[0]}/{total_requests}] {task['model_key']}: ❌ {str(res['error'])[:50]}"
                    )
                else:
                    print(
                        f"[{completed[0]}/{total_requests}] {task['model_key']}: ✓ {res['latency_ms']:.0f}ms"
                    )

            return res

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(run_task, task): task for task in tasks}
            for future in as_completed(futures):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    task = futures[future]
                    results.append(
                        {
                            "model": task["model_key"],
                            "error": str(e),
                            "iteration": task["iteration"],
                        }
                    )

        # Print summaries after parallel run
        print("\n" + "-" * 80)
        for model_key in args.models:
            model_info = get_model_info(model_key)
            model_results = [r for r in results if r.get("model") == model_key]
            successful = [r for r in model_results if not r.get("error")]
            if successful:
                avg_latency = sum(r["latency_ms"] for r in successful) / len(successful)
                avg_ttft = sum(r["ttft_ms"] for r in successful) / len(successful)
                print(
                    f"📊 {model_info['display_name']}: {avg_latency:.0f}ms avg, {len(successful)}/{len(model_results)} success"
                )

    else:
        # Sequential execution (original behavior)
        completed = 0

        for model_key in args.models:
            model_info = get_model_info(model_key)
            print(
                f"\n--- Benchmarking: {model_info['display_name']} ({model_info['model_id']}) ---"
            )

            model_results = []

            for i in range(args.iterations):
                for prompt in prompts:
                    completed += 1
                    print(
                        f"[{completed}/{total_requests}] {model_key}, Iter {i + 1}: '{prompt[:40]}...'"
                    )

                    res = benchmark_oci(
                        args.compartment_id, endpoint, model_key, prompt, args.dry_run
                    )
                    res["iteration"] = i + 1
                    res["prompt_sample"] = prompt[:80]
                    res["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    results.append(res)
                    model_results.append(res)

                    if res.get("error"):
                        print(f"  ❌ Error: {res['error']}")
                    else:
                        print(
                            f"  ✓ TTFT: {res['ttft_ms']:.1f}ms, Latency: {res['latency_ms']:.1f}ms, Tokens: {res['output_tokens']}"
                        )

            # Print model summary
            successful = [r for r in model_results if not r.get("error")]
            if successful:
                avg_latency = sum(r["latency_ms"] for r in successful) / len(successful)
                avg_ttft = sum(r["ttft_ms"] for r in successful) / len(successful)
                print(f"\n  📊 {model_info['display_name']} Summary:")
                print(f"     Avg Latency: {avg_latency:.1f}ms, Avg TTFT: {avg_ttft:.1f}ms")
                print(f"     Success Rate: {len(successful)}/{len(model_results)}")

    total_time = time.time() - start_global
    print(f"\n{'=' * 80}")
    print(f"Benchmark completed in {total_time:.2f}s")
    print(f"Total requests: {completed}")

    # Save results
    output_data = {
        "metadata": {
            "endpoint": endpoint,
            "models": args.models,
            "prompts_count": len(prompts),
            "iterations": args.iterations,
            "parallel": args.parallel,
            "workers": args.workers if args.parallel else 1,
            "dry_run": args.dry_run,
            "total_time_s": round(total_time, 2),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "results": results,
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"Results saved to {args.output}")

    # Print final summary table
    print(f"\n{'=' * 80}")
    print("Summary by Model")
    print(f"{'=' * 80}")
    print(f"{'Model':<25} {'Avg Latency':<15} {'Avg TTFT':<15} {'Success'}")
    print("-" * 80)

    for model_key in args.models:
        model_results = [r for r in results if r["model"] == model_key]
        successful = [r for r in model_results if not r.get("error")]

        if successful:
            avg_latency = sum(r["latency_ms"] for r in successful) / len(successful)
            avg_ttft = sum(r["ttft_ms"] for r in successful) / len(successful)
            print(
                f"{model_key:<25} {avg_latency:>10.1f}ms    {avg_ttft:>10.1f}ms    {len(successful)}/{len(model_results)}"
            )
        else:
            print(f"{model_key:<25} {'N/A':<15} {'N/A':<15} 0/{len(model_results)}")


if __name__ == "__main__":
    main()
