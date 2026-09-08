"""
Unified Benchmark Runner for Agent Reasoning

Supports:
- Agent reasoning strategy benchmarks
- Ollama inference benchmarks
- Comparative analysis and reports
"""

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, Generator, List, Optional

# OCI A10 GPU pricing (VM.GPU.A10.1 shape)
# Price per hour in USD - used to calculate cost for local Ollama inference
# Source: https://www.oracle.com/cloud/compute/pricing/
OCI_A10_HOURLY_PRICE = 1.28  # USD per hour


class BenchmarkType(Enum):
    AGENT_REASONING = "agent_reasoning"
    INFERENCE = "inference"
    EMBEDDINGS = "embeddings"
    OCI_COMPARISON = "oci_comparison"


@dataclass
class BenchmarkTask:
    """A single benchmark task."""

    id: str
    name: str
    category: str
    query: str
    recommended_strategy: str
    description: str = ""


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    task_id: str
    task_name: str
    strategy: str
    model: str
    success: bool
    response: str = ""
    error: Optional[str] = None
    ttft_ms: float = 0.0  # Time to first token
    total_ms: float = 0.0  # Total time
    token_count: int = 0
    tps: float = 0.0  # Tokens per second
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class InferenceResult:
    """Result of an inference benchmark run."""

    source: str  # "ollama" or "oci"
    model: str
    prompt: str
    iteration: int
    success: bool
    latency_ms: float = 0.0
    ttft_ms: float = 0.0
    tps: float = 0.0
    token_count: int = 0
    cost_estimate: float = 0.0
    error: Optional[str] = None


@dataclass
class ComparisonResult:
    """Result of OCI vs Ollama comparison."""

    prompt: str
    ollama_latency_ms: float
    ollama_ttft_ms: float
    ollama_tps: float
    oci_latency_ms: float
    oci_cost: float
    latency_diff_pct: float  # Positive = OCI faster
    winner: str  # "ollama" or "oci"


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""

    benchmark_type: str
    model: str
    timestamp: str
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    avg_latency_ms: float
    avg_ttft_ms: float
    avg_tps: float
    results: List[BenchmarkResult]

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# Benchmark Report: {self.benchmark_type}",
            "",
            f"**Model:** {self.model}",
            f"**Timestamp:** {self.timestamp}",
            f"**Total Tasks:** {self.total_tasks}",
            f"**Successful:** {self.successful_tasks}",
            f"**Failed:** {self.failed_tasks}",
            "",
            "## Performance Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Avg Latency | {self.avg_latency_ms:.2f} ms |",
            f"| Avg TTFT | {self.avg_ttft_ms:.2f} ms |",
            f"| Avg TPS | {self.avg_tps:.2f} |",
            "",
            "## Results by Task",
            "",
            "| Task | Strategy | Latency (ms) | TTFT (ms) | TPS | Status |",
            "|------|----------|--------------|-----------|-----|--------|",
        ]

        for r in self.results:
            status = "✓" if r.success else "✗"
            lines.append(
                f"| {r.task_name[:30]} | {r.strategy} | {r.total_ms:.0f} | {r.ttft_ms:.0f} | {r.tps:.1f} | {status} |"
            )

        return "\n".join(lines)


# Pre-defined benchmark tasks for agent reasoning
AGENT_BENCHMARK_TASKS = [
    BenchmarkTask(
        id="philosophy",
        name="Philosophy Analysis",
        category="Philosophy",
        query="What is the meaning of life? Answer with a mix of biological and philosophical perspectives.",
        recommended_strategy="consistency",
        description="Tests diverse reasoning with self-consistency voting",
    ),
    BenchmarkTask(
        id="logic_riddle",
        name="Logic Riddle",
        category="Logic",
        query="I have a 3-gallon jug and a 5-gallon jug. How can I measure exactly 4 gallons of water?",
        recommended_strategy="tot",
        description="Tests tree-of-thought exploration for puzzle solving",
    ),
    BenchmarkTask(
        id="planning",
        name="Trip Planning",
        category="Planning",
        query="Plan a detailed 3-day itinerary for Tokyo for a history buff who loves samurais and tea.",
        recommended_strategy="decomposed",
        description="Tests problem decomposition for complex planning",
    ),
    BenchmarkTask(
        id="physics",
        name="Relativistic Physics",
        category="Physics",
        query="A train travels at 0.6c for 5 years (train time). How much time has passed on Earth? Explain the steps.",
        recommended_strategy="least_to_most",
        description="Tests incremental solving for multi-step problems",
    ),
    BenchmarkTask(
        id="tool_use",
        name="Tool Use & Search",
        category="Tools",
        query="Who is the current CEO of Google? Calculate the square root of 144.",
        recommended_strategy="react",
        description="Tests ReAct pattern for tool-based reasoning",
    ),
    BenchmarkTask(
        id="code_gen",
        name="Code Generation",
        category="Coding",
        query="Write a Python function that implements binary search on a sorted list. Include docstring and type hints.",
        recommended_strategy="reflection",
        description="Tests self-reflection for code quality",
    ),
    BenchmarkTask(
        id="technical_writing",
        name="Technical Writing",
        category="Writing",
        query="Explain how neural networks learn using backpropagation, gradient descent, and loss functions.",
        recommended_strategy="refinement",
        description="Tests iterative refinement for technical content",
    ),
    BenchmarkTask(
        id="math_proof",
        name="Mathematical Proof",
        category="Math",
        query="Prove that the square root of 2 is irrational.",
        recommended_strategy="cot",
        description="Tests chain-of-thought for logical proofs",
    ),
]

# Pre-defined prompts for inference benchmarks
INFERENCE_BENCHMARK_PROMPTS = [
    "Why is the sky blue?",
    "Write a Python function to compute the Fibonacci sequence.",
    "Explain quantum mechanics to a 5 year old.",
    "What are the main differences between Python and JavaScript?",
    "Summarize the plot of Romeo and Juliet in 3 sentences.",
]


class BenchmarkRunner:
    """
    Unified benchmark runner for agent reasoning strategies.

    Supports real-time streaming of results and report generation.
    """

    def __init__(self, model: str = "gemma3:latest"):
        self.model = model
        self.results: List[BenchmarkResult] = []

    def run_agent_benchmark(
        self,
        tasks: Optional[List[BenchmarkTask]] = None,
        strategies: Optional[List[str]] = None,
        on_task_start: Optional[Callable[[BenchmarkTask, str], None]] = None,
        on_task_complete: Optional[Callable[[BenchmarkResult], None]] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> Generator[BenchmarkResult, None, None]:
        """
        Run agent reasoning benchmarks with real-time streaming.

        Args:
            tasks: List of tasks to run (defaults to AGENT_BENCHMARK_TASKS)
            strategies: List of strategies to test (defaults to task's recommended)
            on_task_start: Callback when task starts
            on_task_complete: Callback when task completes
            on_chunk: Callback for streaming output

        Yields:
            BenchmarkResult for each completed task
        """
        from agent_reasoning.interceptor import AGENT_MAP

        if tasks is None:
            tasks = AGENT_BENCHMARK_TASKS

        for task in tasks:
            # Determine which strategies to run
            task_strategies = strategies if strategies else [task.recommended_strategy]

            for strategy in task_strategies:
                if strategy not in AGENT_MAP:
                    yield BenchmarkResult(
                        task_id=task.id,
                        task_name=task.name,
                        strategy=strategy,
                        model=self.model,
                        success=False,
                        error=f"Unknown strategy: {strategy}",
                    )
                    continue

                if on_task_start:
                    on_task_start(task, strategy)

                # Run the benchmark
                result = self._run_single_agent_task(task, strategy, on_chunk)
                self.results.append(result)

                if on_task_complete:
                    on_task_complete(result)

                yield result

    def _run_single_agent_task(
        self, task: BenchmarkTask, strategy: str, on_chunk: Optional[Callable[[str], None]] = None
    ) -> BenchmarkResult:
        """Run a single agent task and measure performance."""
        from agent_reasoning.interceptor import AGENT_MAP

        agent_class = AGENT_MAP[strategy]
        agent = agent_class(model=self.model)

        response = ""
        token_count = 0
        start_time = time.time()
        first_token_time = None

        try:
            for chunk in agent.stream(task.query):
                if first_token_time is None:
                    first_token_time = time.time()

                response += chunk
                token_count += 1

                if on_chunk:
                    on_chunk(chunk)

            end_time = time.time()

            ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
            total_ms = (end_time - start_time) * 1000
            tps = token_count / (total_ms / 1000) if total_ms > 0 else 0

            return BenchmarkResult(
                task_id=task.id,
                task_name=task.name,
                strategy=strategy,
                model=self.model,
                success=True,
                response=response,
                ttft_ms=round(ttft, 2),
                total_ms=round(total_ms, 2),
                token_count=token_count,
                tps=round(tps, 2),
            )

        except Exception as e:
            return BenchmarkResult(
                task_id=task.id,
                task_name=task.name,
                strategy=strategy,
                model=self.model,
                success=False,
                error=str(e),
            )

    def run_inference_benchmark(
        self,
        prompts: Optional[List[str]] = None,
        iterations: int = 3,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> Generator[Dict, None, None]:
        """
        Run raw inference benchmarks.

        Args:
            prompts: List of prompts to test
            iterations: Number of iterations per prompt
            on_progress: Callback(current, total, prompt) for progress

        Yields:
            Dict with benchmark metrics for each run
        """
        import requests

        if prompts is None:
            prompts = INFERENCE_BENCHMARK_PROMPTS

        url = "http://localhost:11434/api/generate"
        total = len(prompts) * iterations
        current = 0

        for prompt in prompts:
            for i in range(iterations):
                current += 1

                if on_progress:
                    on_progress(current, total, prompt[:50])

                payload = {"model": self.model, "prompt": prompt, "stream": True}

                start_time = time.time()
                first_token_time = None
                response_text = ""
                token_count = 0

                try:
                    with requests.post(url, json=payload, stream=True, timeout=120) as r:
                        r.raise_for_status()
                        for line in r.iter_lines():
                            if line:
                                data = json.loads(line.decode("utf-8"))
                                if first_token_time is None:
                                    first_token_time = time.time()

                                if not data.get("done"):
                                    response_text += data.get("response", "")
                                    token_count += 1

                    end_time = time.time()

                    ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
                    total_ms = (end_time - start_time) * 1000
                    tps = token_count / (total_ms / 1000) if total_ms > 0 else 0

                    yield {
                        "model": self.model,
                        "prompt": prompt[:50],
                        "iteration": i + 1,
                        "ttft_ms": round(ttft, 2),
                        "total_ms": round(total_ms, 2),
                        "token_count": token_count,
                        "tps": round(tps, 2),
                        "success": True,
                        "error": None,
                    }

                except Exception as e:
                    yield {
                        "model": self.model,
                        "prompt": prompt[:50],
                        "iteration": i + 1,
                        "success": False,
                        "error": str(e),
                    }

    def generate_report(self, benchmark_type: str = "agent_reasoning") -> BenchmarkReport:
        """Generate a benchmark report from collected results."""
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        avg_latency = sum(r.total_ms for r in successful) / len(successful) if successful else 0
        avg_ttft = sum(r.ttft_ms for r in successful) / len(successful) if successful else 0
        avg_tps = sum(r.tps for r in successful) / len(successful) if successful else 0

        return BenchmarkReport(
            benchmark_type=benchmark_type,
            model=self.model,
            timestamp=datetime.now().isoformat(),
            total_tasks=len(self.results),
            successful_tasks=len(successful),
            failed_tasks=len(failed),
            avg_latency_ms=round(avg_latency, 2),
            avg_ttft_ms=round(avg_ttft, 2),
            avg_tps=round(avg_tps, 2),
            results=self.results,
        )

    def save_report(self, filepath: str, format: str = "markdown") -> None:
        """Save benchmark report to file."""
        report = self.generate_report()

        if format == "markdown":
            content = report.to_markdown()
        elif format == "json":
            content = json.dumps(asdict(report), indent=2)
        else:
            raise ValueError(f"Unknown format: {format}")

        with open(filepath, "w") as f:
            f.write(content)

    def clear_results(self) -> None:
        """Clear collected results."""
        self.results = []

    def run_oci_benchmark(
        self,
        prompts: Optional[List[str]] = None,
        iterations: int = 3,
        model_id: str = "meta.llama-3.3-70b-instruct",
        compartment_id: Optional[str] = None,
        endpoint: str = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
        profile_name: str = "DEFAULT",
        dry_run: bool = False,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> Generator[InferenceResult, None, None]:
        """
        Run OCI Generative AI benchmark.

        Args:
            prompts: List of prompts to test
            iterations: Number of iterations per prompt
            model_id: OCI model ID
            compartment_id: OCI compartment ID (required unless dry_run)
            endpoint: OCI GenAI endpoint
            dry_run: If True, simulate results without calling API
            on_progress: Callback(current, total, prompt)

        Yields:
            InferenceResult for each completed run
        """
        import random

        if prompts is None:
            prompts = INFERENCE_BENCHMARK_PROMPTS

        total = len(prompts) * iterations
        current = 0

        # Try to import OCI SDK
        oci = None
        if not dry_run:
            try:
                import oci as oci_sdk

                oci = oci_sdk
            except ImportError:
                pass

        for prompt in prompts:
            for i in range(iterations):
                current += 1

                if on_progress:
                    on_progress(current, total, prompt[:50])

                if dry_run:
                    # Simulate OCI performance
                    base_latency = 350.0
                    if "command-r" in model_id.lower():
                        base_latency = 280.0
                    elif "llama" in model_id.lower():
                        base_latency = 400.0

                    latency = base_latency + random.uniform(0, 100)
                    tokens = random.randint(80, 150)
                    cost = (len(prompt) + tokens * 4) * 0.000001

                    yield InferenceResult(
                        source="oci",
                        model=model_id,
                        prompt=prompt[:50],
                        iteration=i + 1,
                        success=True,
                        latency_ms=round(latency, 2),
                        ttft_ms=round(latency * 0.3, 2),  # Estimate TTFT
                        tps=round(tokens / (latency / 1000), 2),
                        token_count=tokens,
                        cost_estimate=round(cost, 8),
                    )
                    continue

                # Real OCI call
                if not oci:
                    yield InferenceResult(
                        source="oci",
                        model=model_id,
                        prompt=prompt[:50],
                        iteration=i + 1,
                        success=False,
                        error="OCI SDK not installed. Run 'pip install oci'.",
                    )
                    continue

                try:
                    config = oci.config.from_file(profile_name=profile_name)

                    # Get compartment_id from config if not provided
                    effective_compartment_id = compartment_id
                    if not effective_compartment_id:
                        # Try to find oci_generative_ai compartment
                        try:
                            identity_client = oci.identity.IdentityClient(config)
                            compartments = identity_client.list_compartments(
                                config.get("tenancy"), compartment_id_in_subtree=True
                            )
                            for c in compartments.data:
                                if c.name == "oci_generative_ai" and c.lifecycle_state == "ACTIVE":
                                    effective_compartment_id = c.id
                                    break
                        except Exception:
                            pass

                    if not effective_compartment_id:
                        effective_compartment_id = config.get("compartment_id") or config.get(
                            "tenancy"
                        )

                    if not effective_compartment_id:
                        yield InferenceResult(
                            source="oci",
                            model=model_id,
                            prompt=prompt[:50],
                            iteration=i + 1,
                            success=False,
                            error="Compartment ID not found in config or parameter",
                        )
                        continue

                    client = oci.generative_ai_inference.GenerativeAiInferenceClient(
                        config=config,
                        service_endpoint=endpoint,
                        retry_strategy=oci.retry.NoneRetryStrategy(),
                        timeout=(10, 240),
                    )

                    # Use GenericChatRequest with STREAMING enabled
                    chat_detail = oci.generative_ai_inference.models.ChatDetails(
                        compartment_id=effective_compartment_id,
                        serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
                            model_id=model_id
                        ),
                        chat_request=oci.generative_ai_inference.models.GenericChatRequest(
                            messages=[
                                oci.generative_ai_inference.models.UserMessage(
                                    content=[
                                        oci.generative_ai_inference.models.TextContent(text=prompt)
                                    ]
                                )
                            ],
                            max_tokens=200,
                            temperature=0.75,
                            is_stream=True,  # Enable streaming for accurate TTFT
                        ),
                    )

                    start_time = time.time()
                    first_token_time = None
                    output_text = ""
                    token_count = 0

                    response = client.chat(chat_detail)

                    # Process streaming response (SSE events)
                    for event in response.data.events():
                        if first_token_time is None:
                            first_token_time = time.time()

                        token_count += 1

                        if event.data:
                            try:
                                data = json.loads(event.data)
                                # Extract text from streaming event
                                if "message" in data:
                                    msg = data["message"]
                                    if "content" in msg:
                                        for c in msg["content"]:
                                            if isinstance(c, dict) and "text" in c:
                                                output_text += c["text"]
                            except json.JSONDecodeError:
                                pass

                    end_time = time.time()

                    ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
                    latency = (end_time - start_time) * 1000
                    tps = token_count / (latency / 1000) if latency > 0 else 0
                    cost = (len(prompt) + len(output_text)) * 0.000001

                    yield InferenceResult(
                        source="oci",
                        model=model_id,
                        prompt=prompt[:50],
                        iteration=i + 1,
                        success=True,
                        latency_ms=round(latency, 2),
                        ttft_ms=round(ttft, 2),
                        tps=round(tps, 2),
                        token_count=token_count,
                        cost_estimate=round(cost, 8),
                    )

                except Exception as e:
                    yield InferenceResult(
                        source="oci",
                        model=model_id,
                        prompt=prompt[:50],
                        iteration=i + 1,
                        success=False,
                        error=str(e)[:200],
                    )

    def run_comparison_benchmark(
        self,
        prompts: Optional[List[str]] = None,
        iterations: int = 3,
        ollama_models: Optional[List[str]] = None,
        oci_model_id: str = "meta.llama-3.3-70b-instruct",
        compartment_id: Optional[str] = None,
        endpoint: str = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
        profile_name: str = "DEFAULT",
        dry_run: bool = False,
        on_ollama_result: Optional[Callable[[InferenceResult], None]] = None,
        on_oci_result: Optional[Callable[[InferenceResult], None]] = None,
        on_comparison: Optional[Callable[[ComparisonResult], None]] = None,
    ) -> Generator[Dict, None, None]:
        """
        Run side-by-side OCI vs Ollama benchmark IN PARALLEL.

        Args:
            prompts: List of prompts to test
            iterations: Number of iterations per prompt
            ollama_models: List of Ollama models to benchmark (default: [self.model])
            oci_model_id: OCI model ID
            compartment_id: OCI compartment ID
            endpoint: OCI GenAI endpoint
            dry_run: Simulate OCI results
            on_ollama_result: Callback for each Ollama result
            on_oci_result: Callback for each OCI result
            on_comparison: Callback for each comparison

        Yields:
            Dict with comparison data for each prompt
        """
        import queue
        import threading

        import requests

        if prompts is None:
            prompts = INFERENCE_BENCHMARK_PROMPTS

        if ollama_models is None:
            ollama_models = [self.model]

        # Shared queue for results from all threads
        result_queue = queue.Queue()
        all_results: Dict[str, List[InferenceResult]] = {model: [] for model in ollama_models}
        all_results["oci"] = []

        def run_ollama_benchmark_for_model(model_name: str):
            """Run Ollama benchmarks for a specific model."""
            url = "http://localhost:11434/api/generate"

            for prompt in prompts:
                for i in range(iterations):
                    payload = {"model": model_name, "prompt": prompt, "stream": True}

                    start_time = time.time()
                    first_token_time = None
                    response_text = ""
                    token_count = 0

                    try:
                        with requests.post(url, json=payload, stream=True, timeout=180) as r:
                            r.raise_for_status()
                            for line in r.iter_lines():
                                if line:
                                    data = json.loads(line.decode("utf-8"))
                                    if first_token_time is None:
                                        first_token_time = time.time()

                                    if not data.get("done"):
                                        response_text += data.get("response", "")
                                        token_count += 1

                        end_time = time.time()
                        ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
                        total_ms = (end_time - start_time) * 1000
                        tps = token_count / (total_ms / 1000) if total_ms > 0 else 0

                        # Calculate cost based on A10 GPU hourly rental
                        # cost = (hourly_price / 3600 seconds) * processing_time_seconds
                        processing_seconds = total_ms / 1000
                        cost = (OCI_A10_HOURLY_PRICE / 3600) * processing_seconds

                        result = InferenceResult(
                            source="ollama",
                            model=model_name,
                            prompt=prompt[:50],
                            iteration=i + 1,
                            success=True,
                            latency_ms=round(total_ms, 2),
                            ttft_ms=round(ttft, 2),
                            tps=round(tps, 2),
                            token_count=token_count,
                            cost_estimate=round(cost, 8),
                        )
                        result_queue.put({"type": "ollama", "model": model_name, "result": result})

                    except Exception as e:
                        result = InferenceResult(
                            source="ollama",
                            model=model_name,
                            prompt=prompt[:50],
                            iteration=i + 1,
                            success=False,
                            error=str(e),
                        )
                        result_queue.put({"type": "ollama", "model": model_name, "result": result})

            result_queue.put({"type": "ollama_done", "model": model_name})

        def run_oci_benchmarks():
            """Run all OCI benchmarks and put results in queue."""
            for result in self.run_oci_benchmark(
                prompts=prompts,
                iterations=iterations,
                model_id=oci_model_id,
                compartment_id=compartment_id,
                endpoint=endpoint,
                profile_name=profile_name,
                dry_run=dry_run,
            ):
                result_queue.put({"type": "oci", "result": result})

            result_queue.put({"type": "oci_done"})

        # Start all benchmark threads (one per Ollama model + one for OCI)
        threads = []

        for model in ollama_models:
            t = threading.Thread(target=run_ollama_benchmark_for_model, args=(model,))
            threads.append(("ollama", model, t))
            t.start()

        oci_thread = threading.Thread(target=run_oci_benchmarks)
        threads.append(("oci", oci_model_id, oci_thread))
        oci_thread.start()

        # Track which threads are done
        done_count = 0
        total_threads = len(threads)

        while done_count < total_threads:
            try:
                item = result_queue.get(timeout=0.1)

                if item["type"] == "ollama_done":
                    done_count += 1
                    continue
                elif item["type"] == "oci_done":
                    done_count += 1
                    continue

                # Store results by model
                if item["type"] == "ollama":
                    model_name = item.get("model", self.model)
                    all_results[model_name].append(item["result"])
                    if on_ollama_result:
                        on_ollama_result(item["result"])
                elif item["type"] == "oci":
                    all_results["oci"].append(item["result"])
                    if on_oci_result:
                        on_oci_result(item["result"])

                yield item

            except queue.Empty:
                continue

        # Wait for all threads to finish
        for _, _, t in threads:
            t.join()

        # Generate comparisons (find winner among all models for each prompt)
        for prompt in prompts:
            prompt_key = prompt[:50]

            # Collect results per model for this prompt
            model_stats = {}

            for model in ollama_models:
                runs = [r for r in all_results[model] if r.prompt == prompt_key and r.success]
                if runs:
                    model_stats[model] = {
                        "latency": sum(r.latency_ms for r in runs) / len(runs),
                        "ttft": sum(r.ttft_ms for r in runs) / len(runs),
                        "tps": sum(r.tps for r in runs) / len(runs),
                        "source": "ollama",
                    }

            oci_runs = [r for r in all_results["oci"] if r.prompt == prompt_key and r.success]
            if oci_runs:
                model_stats["oci"] = {
                    "latency": sum(r.latency_ms for r in oci_runs) / len(oci_runs),
                    "ttft": sum(r.ttft_ms for r in oci_runs) / len(oci_runs),
                    "tps": sum(r.tps for r in oci_runs) / len(oci_runs),
                    "cost": sum(r.cost_estimate for r in oci_runs) / len(oci_runs),
                    "source": "oci",
                }

            if len(model_stats) >= 2:
                # Find winner (lowest latency)
                winner = min(model_stats.keys(), key=lambda m: model_stats[m]["latency"])

                # For backward compatibility, use first ollama model for comparison result
                first_ollama = ollama_models[0] if ollama_models else None
                if first_ollama and first_ollama in model_stats and "oci" in model_stats:
                    ollama_lat = model_stats[first_ollama]["latency"]
                    oci_lat = model_stats["oci"]["latency"]
                    diff_pct = ((ollama_lat - oci_lat) / ollama_lat * 100) if ollama_lat > 0 else 0

                    comparison = ComparisonResult(
                        prompt=prompt_key,
                        ollama_latency_ms=round(ollama_lat, 2),
                        ollama_ttft_ms=round(model_stats[first_ollama]["ttft"], 2),
                        ollama_tps=round(model_stats[first_ollama]["tps"], 2),
                        oci_latency_ms=round(oci_lat, 2),
                        oci_cost=round(model_stats["oci"].get("cost", 0), 8),
                        latency_diff_pct=round(diff_pct, 1),
                        winner=winner,
                    )

                    if on_comparison:
                        on_comparison(comparison)

                    # Include all model stats in the yield
                    yield {
                        "type": "comparison",
                        "result": comparison,
                        "all_models": model_stats,
                        "winner": winner,
                    }
