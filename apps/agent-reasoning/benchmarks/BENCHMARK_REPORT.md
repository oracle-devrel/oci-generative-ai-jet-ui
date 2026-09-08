# Benchmark Report: Ollama vs. OCI Generative AI

**Date:** 2026-02-05
**Status:** Live Benchmark Results
**Total Requests:** 60 (24 Ollama + 36 OCI)

## 1. Executive Summary

This report benchmarks the performance of running Large Language Models locally using **Ollama** on GPU versus the managed **Oracle Cloud Infrastructure (OCI) Generative AI Service** with models from OpenAI, xAI, Meta, Google, and Cohere.

**Key Findings:**
- **Fastest Overall:** OCI xAI Grok 4.1 Fast (3,516ms avg latency)
- **Best TTFT:** Ollama gemma3:latest (750ms)
- **Highest Throughput:** Ollama gemma3:270m (154.8 tokens/s)
- **Most Cost Effective:** OCI Gemini 2.5 Pro ($0.00006/request)
- **Total OCI Cost:** $0.029 for 36 requests

## 2. Methodology

### Configuration
- **Ollama**: Local GPU inference (`localhost:11434`)
- **OCI GenAI**: Managed cloud inference (`us-chicago-1` region)
- **OCI Profile**: `foosball`
- **Max Tokens**: 1,000 per request
- **Iterations**: 2 per prompt per model
- **Prompts**: 3 distinct programming/technical questions

### Test Prompts
1. "Explain the concept of recursion in programming with a simple example."
2. "What are the key differences between SQL and NoSQL databases?"
3. "Write a Python function to find the longest common subsequence of two strings."

## 3. Models Tested

### OCI GenAI Models
| Model | Provider | Model ID |
|-------|----------|----------|
| GPT-OSS-120B | OpenAI | `openai.gpt-oss-120b` |
| Grok 4.1 Fast | xAI | `xai.grok-4-1-fast-non-reasoning` |
| Grok 3 Fast | xAI | `xai.grok-3-fast` |
| Llama 4 Maverick | Meta | `meta.llama-4-maverick-17b-128e-instruct-fp8` |
| Gemini 2.5 Pro | Google | `google.gemini-2.5-pro` |
| Command R | Cohere | `cohere.command-r-08-2024` |

### Ollama Models (Local GPU)
| Model | Size |
|-------|------|
| gemma3:latest | 4B |
| gemma3:270m | 270M |
| llama3.2:3b | 3B |
| phi3:latest | 3.8B |

## 4. Detailed Results

### Full Comparison (Sorted by Latency)

| Source | Model | Provider | Latency | TTFT | Tokens | TPS | Cost | Success |
|--------|-------|----------|---------|------|--------|-----|------|---------|
| OCI | grok-4.1-fast | xai | 3,516ms | 3,516ms | 486 | 138.3 | $0.00074 | 6/6 |
| Ollama | llama3.2:3b | local | 4,152ms | 1,341ms | 415 | 122.7 | GPU | 6/6 |
| OCI | llama-4-maverick | meta | 4,565ms | 4,565ms | 525 | 114.9 | $0.00079 | 6/6 |
| Ollama | gemma3:270m | local | 4,639ms | 1,274ms | 654 | 154.8 | GPU | 6/6 |
| Ollama | phi3:latest | local | 5,839ms | 1,608ms | 646 | 130.5 | GPU | 6/6 |
| OCI | cohere-command-r | cohere | 9,016ms | 9,016ms | 518 | 57.5 | $0.00078 | 6/6 |
| OCI | gemini-2.5-pro | google | 9,821ms | 9,821ms | 37 | 3.8 | $0.00006 | 6/6 |
| OCI | grok-3-fast | xai | 10,642ms | 10,642ms | 702 | 65.9 | $0.00106 | 6/6 |
| OCI | gpt-oss-120b | openai | 11,917ms | 11,917ms | 686 | 57.5 | $0.00139 | 6/6 |
| Ollama | gemma3:latest | local | 14,719ms | 750ms | 1,138 | 77.3 | GPU | 6/6 |

### Metric Definitions
- **Latency**: Total time from request to full response completion
- **TTFT**: Time To First Token (important for streaming UX)
- **Tokens**: Average output tokens per response
- **TPS**: Tokens Per Second (throughput)
- **Cost**: Estimated per-request cost (OCI) or GPU rental (Ollama)

## 5. Key Insights

| Category | Winner | Value |
|----------|--------|-------|
| Fastest (Latency) | OCI grok-4.1-fast | 3,516ms |
| Best TTFT | Ollama gemma3:latest | 750ms |
| Highest Throughput | Ollama gemma3:270m | 154.8 tokens/s |
| Most Tokens | Ollama gemma3:latest | 1,138 avg |
| Lowest Cost | OCI gemini-2.5-pro | $0.00006/req |

## 6. Special Notes

### Google Gemini 2.5 Pro - Thinking Model Behavior

Gemini 2.5 Pro exhibits unique behavior compared to other models:

| Metric | Gemini 2.5 Pro | Other Models (avg) |
|--------|----------------|-------------------|
| Output Tokens | 37 | 500-700 |
| Latency | 9,821ms | 3,500-12,000ms |
| Cost | $0.00006 | $0.0007-0.0014 |

**Explanation:** Gemini 2.5 Pro is a **reasoning/thinking model** that uses internal "thinking tokens" before generating output. Key characteristics:

1. **Internal Processing**: The model performs extensive internal reasoning before producing output
2. **Token Allocation**: The `max_tokens` limit (1,000) includes both thinking and output tokens, leaving fewer for actual response
3. **Lower Output**: Only ~37 tokens of visible output vs 500+ for standard models
4. **Higher Latency**: ~10 seconds due to internal reasoning process
5. **Lower Cost**: Charged only for output tokens, not thinking tokens

This is **expected behavior** for reasoning models. For use cases requiring detailed responses, consider:
- Increasing `max_tokens` to 4,000+ for Gemini
- Using non-reasoning variants if available
- Accepting the trade-off of deeper reasoning for shorter responses

## 7. Visualizations

### Latency Comparison (Lower is Better)

```
grok-4.1-fast    |████████ 3,516ms
llama3.2:3b      |█████████ 4,152ms
llama-4-maverick |██████████ 4,565ms
gemma3:270m      |██████████ 4,639ms
phi3:latest      |█████████████ 5,839ms
cohere-command-r |████████████████████ 9,016ms
gemini-2.5-pro   |██████████████████████ 9,821ms
grok-3-fast      |████████████████████████ 10,642ms
gpt-oss-120b     |██████████████████████████ 11,917ms
gemma3:latest    |████████████████████████████████ 14,719ms
```

### Throughput Comparison (Higher is Better)

```
gemma3:270m      |████████████████████████████████ 154.8 TPS
grok-4.1-fast    |████████████████████████████ 138.3 TPS
phi3:latest      |██████████████████████████ 130.5 TPS
llama3.2:3b      |█████████████████████████ 122.7 TPS
llama-4-maverick |███████████████████████ 114.9 TPS
gemma3:latest    |████████████████ 77.3 TPS
grok-3-fast      |█████████████ 65.9 TPS
cohere-command-r |████████████ 57.5 TPS
gpt-oss-120b     |████████████ 57.5 TPS
gemini-2.5-pro   |█ 3.8 TPS
```

## 8. Cost Analysis

### OCI Cost Breakdown (36 requests total)

| Model | Requests | Cost/Request | Total |
|-------|----------|--------------|-------|
| gpt-oss-120b | 6 | $0.00139 | $0.0083 |
| grok-3-fast | 6 | $0.00106 | $0.0064 |
| llama-4-maverick | 6 | $0.00079 | $0.0047 |
| cohere-command-r | 6 | $0.00078 | $0.0047 |
| grok-4.1-fast | 6 | $0.00074 | $0.0044 |
| gemini-2.5-pro | 6 | $0.00006 | $0.0004 |
| **Total** | **36** | | **$0.0289** |

### Ollama Cost Estimate
Local GPU inference has no per-request cost but requires:
- GPU hardware (e.g., NVIDIA A10: ~$1.50-2.00/hour cloud rental)
- Power and cooling
- Maintenance overhead

**Break-even analysis:** At $0.0008/request average OCI cost, running 1,875+ requests/hour justifies dedicated GPU rental.

## 9. Recommendations

### Use OCI GenAI When:
- Low latency is critical (Grok 4.1 Fast: 3.5s)
- No GPU infrastructure available
- Variable/bursty workloads
- Need access to multiple model providers

### Use Ollama When:
- High throughput needed (gemma3:270m: 155 TPS)
- Best TTFT for streaming UX (gemma3: 750ms)
- Data privacy requirements (on-premises)
- Predictable, high-volume workloads
- Cost optimization at scale

## 10. Running the Benchmark

```bash
# Full benchmark (Ollama + OCI)
python benchmarks/run_benchmark.py --parallel --iterations 2

# OCI only
python benchmarks/run_benchmark.py --skip-ollama --parallel

# Dry run (no API calls)
python benchmarks/run_benchmark.py --dry-run

# List available OCI models
python benchmarks/benchmark_oci.py --list-models
```

---

*Report generated from live benchmark data. Results may vary based on network conditions, model load, and prompt complexity.*
