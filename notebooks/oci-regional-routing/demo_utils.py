import oci
from IPython.display import JSON, Markdown, display


def create_responses_clients(config_profile, direct_region, profile_region, compartment_id):
    import httpx
    from openai import OpenAI
    from oci_genai_auth import OciSessionAuth, OciUserPrincipalAuth

    config = oci.config.from_file(profile_name=config_profile)
    auth_class = OciSessionAuth if "security_token_file" in config else OciUserPrincipalAuth
    auth = auth_class(profile_name=config_profile)

    def responses_client(region):
        return OpenAI(
            base_url=f"https://inference.generativeai.{region}.oci.oraclecloud.com/v1",
            api_key="not-used",
            default_headers={"CompartmentId": compartment_id},
            http_client=httpx.Client(auth=auth, follow_redirects=False),
            timeout=httpx.Timeout(120, connect=10),
            max_retries=0,
        )

    profile_client = oci.generative_ai.GenerativeAiClient(
        {**config, "region": profile_region}, signer=auth.signer,
        retry_strategy=oci.retry.NoneRetryStrategy(), timeout=(10, 120),
    )
    return responses_client(direct_region), responses_client(profile_region), profile_client


def show_routing_result(response):
    region = response.headers.get("x-genai-selected-region")
    heading = f"Routed to {region}" if region else "Routing region not returned"
    display(Markdown(f"## {heading}\n\nSource: `x-genai-selected-region` response header."))


def show_responses_result(response):
    result = response.parse().model_dump()
    print("\n".join(
        part["text"] for item in result.get("output", [])
        for part in item.get("content", []) if part.get("type") == "output_text"
    ))
    display(JSON({
        "selected_oci_region": response.headers.get("x-genai-selected-region"),
        "model": result.get("model"),
        "status": result.get("status"),
        "usage": result.get("usage"),
        "request_id": response.headers.get("opc-request-id"),
    }, root="Request details", expanded=True))
