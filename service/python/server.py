import asyncio
import websockets
import json
import oci
from throttler import throttle

#TODO: Update this section with your tenancy details
compartment_id = "ocid1.compartment.oc1.."
CONFIG_PROFILE = "DEFAULT"
config = oci.config.from_file("~/.oci/config", CONFIG_PROFILE)
endpoint = "https://inference.generativeai.<region>.oci.oraclecloud.com"
generative_ai_inference_client = (
    oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=endpoint,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240),
    )
)

@throttle(rate_limit=15, period=65.0)
async def generate_ai_response(prompts):
    prompt = ""
    cohere_generate_text_request = (
        oci.generative_ai_inference.models.CohereLlmInferenceRequest()
    )
    cohere_generate_text_request.prompt = prompts
    cohere_generate_text_request.is_stream = (
        False  # SDK doesn't support streaming responses, feature is under development
    )
    cohere_generate_text_request.max_tokens = 1000
    cohere_generate_text_request.temperature = 0.75
    cohere_generate_text_request.top_p = 0.7
    cohere_generate_text_request.frequency_penalty = 1.0

    generate_text_detail = oci.generative_ai_inference.models.GenerateTextDetails()
    generate_text_detail.serving_mode = (
        oci.generative_ai_inference.models.OnDemandServingMode(
            model_id="cohere.command"
        )
    )
    generate_text_detail.compartment_id = compartment_id
    generate_text_detail.inference_request = cohere_generate_text_request

    if "<compartment_ocid>" in compartment_id:
        print("ERROR:Please update your compartment id in target python file")
        quit()

    generate_text_response = generative_ai_inference_client.generate_text(
        generate_text_detail
    )

    # Print result
    print("**************************Generate Texts Result**************************")
    print(vars(generate_text_response))

    return generate_text_response


async def handle_websocket(websocket, path):
    try:
        while True:
            data = await websocket.recv()
            objData = json.loads(data)
            prompt = list(objData.items())[0][1]
            if list(objData.items())[0][0] == "question":
                response = await generate_ai_response(prompt)
                answer = response.data.inference_response.generated_texts[0].text
                buidJSON = {"answer": answer}
                await websocket.send(json.dumps(buidJSON))
    except websockets.exceptions.ConnectionClosedOK as e:
        print(f"Connection closed: {e}")


async def start_server():
    await websockets.serve(handle_websocket, "localhost", 1234 )


asyncio.get_event_loop().run_until_complete(start_server())
asyncio.get_event_loop().run_forever()
