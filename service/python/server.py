import asyncio
import websockets
import json
import oci
from throttler import throttle

# TODO: Please update config profile name and use the compartmentId that has policies grant permissions for using Generative AI Service
compartment_id = "ocid1.compartment.oc1.."
CONFIG_PROFILE = "DEFAULT"
config = oci.config.from_file('~/.oci/config', CONFIG_PROFILE)

# Service endpoint
endpoint = "https://inference.generativeai.oci.oraclecloud.com"
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
    llm_inference_request = (
        oci.generative_ai_inference.models.CohereLlmInferenceRequest()
    )
    llm_inference_request.prompt = prompts
    llm_inference_request.max_tokens = 1000
    llm_inference_request.temperature = 0.75
    llm_inference_request.top_p = 0.7
    llm_inference_request.frequency_penalty = 1.0

    generate_text_detail = oci.generative_ai_inference.models.GenerateTextDetails()
    generate_text_detail.serving_mode = oci.generative_ai_inference.models.DedicatedServingMode(endpoint_id="ocid1.generativeaiendpoint.oc1.us-chicago-1.amaaaaaaeras5xiavrsefrftfupp42lnniddgjnxuwbv5jypl64i7ktan65a")

    generate_text_detail.compartment_id = compartment_id
    generate_text_detail.inference_request = llm_inference_request

    if "<compartment_ocid>" in compartment_id:
        print("ERROR:Please update your compartment id in target python file")
        quit()

    generate_text_response = generative_ai_inference_client.generate_text(generate_text_detail)
    # Print result
    print("**************************Generate Texts Result**************************")
    print(vars(generate_text_response))

    return generate_text_response

@throttle(rate_limit=15, period=65.0)
async def generate_ai_summary(pdf):
        
    # You can also load the summary text from a file, or as a parameter in main
    with open('files/summarize_data.txt', 'r') as file:
       text_to_summarize = file.read()

    summarize_text_detail = oci.generative_ai_inference.models.SummarizeTextDetails()
    summarize_text_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(model_id="cohere.command")
    summarize_text_detail.compartment_id = compartment_id
    summarize_text_detail.input = text_to_summarize
    summarize_text_detail.additional_command = "Generate a teaser summary for this Markdown file. Share an interesting insight to captivate attention."
    summarize_text_detail.extractiveness = "AUTO" # HIGH, LOW
    summarize_text_detail.format = "AUTO" # brackets, paragraph
    summarize_text_detail.length = "LONG" # high, AUTO
    summarize_text_detail.temperature = .25 # [0,1]

    if "<compartment_ocid>" in compartment_id:
        print("ERROR:Please update your compartment id in target python file")
        quit()

    summarize_text_response = generative_ai_inference_client.summarize_text(summarize_text_detail)

    # Print result
    #print("**************************Summarize Texts Result**************************")
    #print(summarize_text_response.data)

    return summarize_text_response.data

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
            #add PDF handling here
                
    except websockets.exceptions.ConnectionClosedOK as e:
        print(f"Connection closed: {e}")


async def start_server():
    await websockets.serve(handle_websocket, "localhost", 1986 )


asyncio.get_event_loop().run_until_complete(start_server())
asyncio.get_event_loop().run_forever()
