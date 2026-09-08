# OCI Generative AI Integration for PicoOraClaw

This module provides **OCI Generative AI** as an optional LLM backend for PicoOraClaw. It runs a local OpenAI-compatible proxy that authenticates with OCI using your `~/.oci/config` credentials and forwards requests to the OCI GenAI inference endpoint.

The default LLM backend remains **Ollama** -- this is an optional alternative for users who want to leverage OCI-hosted models.

## Prerequisites

- Python 3.11+
- A configured `~/.oci/config` profile with valid OCI credentials
- An OCI compartment with access to the Generative AI service

## Quick Start

1. **Install dependencies:**
   ```bash
   cd oci-genai
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export OCI_PROFILE=DEFAULT
   export OCI_REGION=us-chicago-1
   export OCI_COMPARTMENT_ID=ocid1.compartment.oc1..your-compartment-ocid
   ```

3. **Start the proxy:**
   ```bash
   python proxy.py
   # Proxy runs at http://localhost:9999/v1
   ```

4. **Configure PicoOraClaw** (`~/.picooraclaw/config.json`):
   ```json
   {
     "agents": {
       "defaults": {
         "provider": "openai",
         "model": "meta.llama-3.3-70b-instruct",
         "max_tokens": 8192,
         "temperature": 0.7
       }
     },
     "providers": {
       "openai": {
         "api_key": "oci-genai",
         "api_base": "http://localhost:9999/v1"
       }
     }
   }
   ```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OCI_PROFILE` | `DEFAULT` | OCI config profile name from `~/.oci/config` |
| `OCI_REGION` | `us-chicago-1` | OCI region for the GenAI service endpoint |
| `OCI_COMPARTMENT_ID` | *(required)* | OCI compartment OCID |
| `OCI_PROXY_PORT` | `9999` | Local port for the proxy server |

## Available OCI GenAI Models

| Model ID | Description |
|---|---|
| `xai.grok-4.20` | xAI Grok 4.20 (reasoning + non-reasoning) |
| `xai.grok-4.20-multi-agent` | xAI Grok 4.20 Multi-Agent (real-time multi-agent research) |
| `meta.llama-3.3-70b-instruct` | Meta Llama 3.3 70B Instruct |
| `xai.grok-3-mini` | xAI Grok 3 Mini |
| `cohere.command-r-plus` | Cohere Command R+ |
| `cohere.command-r` | Cohere Command R |
| `meta.llama-3.1-405b-instruct` | Meta Llama 3.1 405B Instruct |

Model availability varies by region. Check the [OCI GenAI documentation](https://docs.oracle.com/en-us/iaas/Content/generative-ai/home.htm) for the latest list.

## How It Works

The proxy translates standard OpenAI API requests into OCI-authenticated requests:

```
PicoOraClaw (Go) --> localhost:9999/v1 (proxy.py) --> OCI GenAI endpoint
                     OpenAI-compatible              OCI User Principal Auth
```

- The proxy uses the `oci-openai` library which wraps the standard OpenAI Python client with OCI authentication
- Authentication uses OCI User Principal Auth from your `~/.oci/config` file
- No separate API keys are needed -- your existing OCI credentials handle everything

## OCI Credentials Setup

If you don't have `~/.oci/config` set up yet:

```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaaexample
fingerprint=aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99
tenancy=ocid1.tenancy.oc1..aaaaaaaaexample
region=us-chicago-1
key_file=~/.oci/oci_api_key.pem
```

See the [OCI SDK Configuration](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm) guide for details.

## Documentation

- [OCI Generative AI Service](https://docs.oracle.com/en-us/iaas/Content/generative-ai/home.htm)
- [oci-openai Python Library](https://pypi.org/project/oci-openai/)
- [OCI SDK Configuration](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm)
