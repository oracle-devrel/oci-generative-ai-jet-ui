# OCI regional routing demo

Compare direct and routed Responses API calls. An image under the notebook title shows both paths.

## Setup

Use Python 3.11+ and an existing OCI profile in `~/.oci/config` with permission to invoke Generative AI and read routing profiles. API signing keys and authenticated sessions are supported.

From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Configuration

Create a routing profile in OCI Console with your model and target regions. Select only that model to compare direct and routed calls to the same model.

If `demo_config.json` does not exist, copy `demo_config.example.json` to it. Set these values:

| Setting | Value |
| --- | --- |
| `oci_profile` | Profile name in `~/.oci/config` |
| `compartment_id` | Compartment OCID for inference |
| `routing_profile_id` | Routing-profile OCID |
| `model_id` | Model supported in your chosen regions |
| `direct_region` | Region for the direct call |
| `profile_region` | Region where the routing profile was created |

## Run

```bash
jupyter lab regional-router-demo.ipynb
```

Run the cells in order. Both calls use the same prompt and generation settings. The `selected_oci_region` field in the response details shows the destination reported by the `x-genai-selected-region` header.

The notebook uses the compartment-scoped `/v1/responses` endpoint through the OpenAI SDK with OCI authentication, `CompartmentId`, and `store: false`. Both calls use `responses.with_raw_response.create()` so the routing response headers remain available.

Inference calls incur charges in your OCI tenancy.
