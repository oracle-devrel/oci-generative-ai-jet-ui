# Benchmark Suite: Ollama vs. OCI Generative AI

Compare local Ollama inference (A10 GPU) against Oracle Cloud Infrastructure (OCI) Generative AI Service.

## Quick Start

```bash
# Run full benchmark (both Ollama and OCI)
python benchmarks/run_benchmark.py

# Run OCI only (skip local Ollama)
python benchmarks/run_benchmark.py --skip-ollama

# Run with fewer iterations
python benchmarks/run_benchmark.py --iterations 1

# Dry run (no API calls)
python benchmarks/run_benchmark.py --dry-run

# Compare existing results
python benchmarks/run_benchmark.py --compare-only
```

## Configuration

All settings are stored in `benchmarks/config.json`:

```json
{
  "oci": {
    "profile": "foosball",
    "compartment_id": "ocid1.compartment.oc1...",
    "region": "us-chicago-1",
    "endpoint": "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
  },
  "models": {
    "oci": [...],
    "ollama": [...]
  }
}
```

## Available OCI Models

| Key | Model | Provider | Avg Latency |
|-----|-------|----------|-------------|
| `llama-4-maverick` | Meta Llama 4 Maverick 17B | Meta | ~1300ms |
| `grok-4.1-fast` | xAI Grok 4.1 Fast | xAI | ~1750ms |
| `gpt-oss-120b` | OpenAI GPT-OSS-120B | OpenAI | ~2150ms |
| `grok-3-fast` | xAI Grok 3 Fast | xAI | ~2640ms |
| `gemini-2.5-pro` | Google Gemini 2.5 Pro | Google | ~2930ms |
| `cohere-command-r` | Cohere Command R | Cohere | ~3035ms |

List all models:
```bash
python benchmarks/benchmark_oci.py --list-models
```

## Metrics

- **TTFT (Time To First Token)**: Latency from request to the first generated token
- **End-to-End Latency**: Total time for the request to complete
- **Throughput (Tokens/s)**: Output tokens generated per second
- **Cost**: Estimated cost per request

## Individual Scripts

### OCI Benchmark
```bash
# Uses config.json settings (no args needed)
python benchmarks/benchmark_oci.py

# Override with specific models
python benchmarks/benchmark_oci.py --models grok-4.1-fast gemini-2.5-pro
```

### Ollama Benchmark
```bash
python benchmarks/benchmark_ollama.py --models gemma3:latest llama3.2:3b
```

### Compare Results
```bash
python benchmarks/compare_results.py
```

## Setup

### Prerequisites
1. **Python 3.10+**
2. **OCI SDK**: `pip install oci`
3. **OCI CLI configured**: Valid `~/.oci/config` with the `foosball` profile
4. **For Ollama**: Local Ollama server (`ollama serve`)

### OCI Configuration

The benchmark uses the `foosball` profile from `~/.oci/config`:
- Region: `us-chicago-1`
- Compartment: `oci_generative_ai`

## Output Files

- `ollama_results.json` - Ollama benchmark results
- `oci_results.json` - OCI GenAI benchmark results
- `config.json` - Saved configuration

## Example Output

```
================================================================================
BENCHMARK COMPARISON: Ollama (Local) vs OCI GenAI (Cloud)
================================================================================
| Source | Model            | Provider | Avg Latency | Tokens/s | Cost     |
|--------|------------------|----------|-------------|----------|----------|
| Ollama | gemma3:latest    | local    | 1200.0ms    | 83.3     | GPU      |
| OCI    | llama-4-maverick | meta     | 1297.1ms    | 133.1    | $0.00027 |
| OCI    | grok-4.1-fast    | xai      | 1754.3ms    | 89.5     | $0.00024 |
| OCI    | gpt-oss-120b     | openai   | 2152.0ms    | 48.7     | $0.00023 |
================================================================================
```
