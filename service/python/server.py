import oci
import asyncio
import websockets
import json
from throttler import throttle
from pypdf import PdfReader
from io import BytesIO
from typing import Any, Dict, List
import re
from types import SimpleNamespace

with open('config.json') as f:
    config = json.load(f)

# Load configuration parameters 
compartment_id = config['compartment_id']
CONFIG_PROFILE = config['config_profile']
endpoint = config['service_endpoint']
model_type = config['model_type']
model_id = config[f'{model_type}_model_id']

config = oci.config.from_file('~/.oci/config', CONFIG_PROFILE)

generative_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
    config=config,
    service_endpoint=endpoint,
    retry_strategy=oci.retry.NoneRetryStrategy(),
    timeout=(10, 240)
)

chat_detail = oci.generative_ai_inference.models.ChatDetails()

# Define a function to generate an AI response
@throttle(rate_limit=15, period=65.0)
async def generate_ai_response(prompts):
    # Determine the request type based on the model type
    if model_type == 'cohere':
        chat_request = oci.generative_ai_inference.models.CohereChatRequest()
        chat_request.max_tokens = 2000
        chat_request.temperature = 0.25
        chat_request.frequency_penalty = 0
        chat_request.top_p = 0.75
        chat_request.top_k = 0
    elif model_type == 'llama':
        chat_request = oci.generative_ai_inference.models.GenericChatRequest()
        chat_request.api_format = oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
        chat_request.max_tokens = 2000
        chat_request.temperature = 1
        chat_request.frequency_penalty = 0
        chat_request.presence_penalty = 0
        chat_request.top_p = 0.75
        chat_request.top_k = -1
    else:
        raise ValueError("Unsupported model type")

    # Process the prompts
    if isinstance(prompts, str):
        if model_type == 'cohere':
            chat_request.message = prompts
        else:
            content = oci.generative_ai_inference.models.TextContent()
            content.text = prompts
            message = oci.generative_ai_inference.models.Message()
            message.role = "USER"
            message.content = [content]
            chat_request.messages = [message]
    elif isinstance(prompts, list):
        chat_request.messages = prompts
    else:
        raise ValueError("Invalid input type for generate_ai_response")

    # Set up the chat detail object
    chat_detail.chat_request = chat_request
    on_demand_mode = oci.generative_ai_inference.models.OnDemandServingMode(model_id=model_id)
    chat_detail.serving_mode = on_demand_mode
    chat_detail.compartment_id = compartment_id

    # Send the request and get the response
    chat_response = generative_ai_inference_client.chat(chat_detail)

    # Validate the compartment ID
    if "<compartment_ocid>" in compartment_id:
        print("ERROR: Please update your compartment id in target python file")
        quit()

    # Print the chat result
    print("**************************Chat Result**************************")
    print(vars(chat_response))

    return chat_response

async def parse_pdf(file: BytesIO) -> List[str]:
    pdf = PdfReader(file)
    output = []
    for page in pdf.pages:
        text = page.extract_text()
        text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
        text = re.sub(r"(?<!\n\s)\n(?!\s\n)", " ", text.strip())
        text = re.sub(r"\n\s*\n", "\n\n", text)
        output.append(text)
    return output

async def handle_websocket(websocket, path):
    try:
        while True:
            data = await websocket.recv()
            if isinstance(data, str):
                objData = json.loads(data, object_hook=lambda d: SimpleNamespace(**d))
                if objData.msgType == "question":
                    prompt = objData.data
                    response = await generate_ai_response(prompt)
                    
                    if model_type == 'llama':
                        answer = response.data.chat_response.choices[0].message.content[0].text
                    elif model_type == 'cohere':
                        answer = response.data.chat_response.text
                    else:
                        answer = ""
                        
                    buidJSON = {"msgType": "answer", "data": answer}
                    await websocket.send(json.dumps(buidJSON))
                elif objData.msgType == "summary":
                    pdfFileObj = BytesIO(objData.data)
                    output = await parse_pdf(pdfFileObj)
                    chunk_size = 512
                    chunks = [' '.join(output[i:i + chunk_size]) for i in range(0, len(output), chunk_size)]
                    
                    print(f"Processing {len(chunks)} chunks...")
                    
                    summaries = []
                    for index, chunk in enumerate(chunks):
                        print(f"Processing chunk {index+1}/{len(chunks)}...")
                        response = await generate_ai_response(f"Summarize: {chunk}")
                        if model_type == 'llama':
                            summary = response.data.chat_response.choices[0].message.content[0].text
                        elif model_type == 'cohere':
                            summary = response.data.chat_response.text
                        else:
                            summary = ""
                        summaries.append(summary)
                        
                    final_summary = ' '.join(summaries)
                    buidJSON = {"msgType": "summary", "data": final_summary}
                    await websocket.send(json.dumps(buidJSON))
            else:
                objData = data.split(b'\r\n\r\n')
                metadata = json.loads(objData[0].decode('utf-8'), object_hook=lambda d: SimpleNamespace(**d))
                pdfFileObj = BytesIO(objData[1])
                output = await parse_pdf(pdfFileObj)
                chunk_size = 512
                chunks = [' '.join(output[i:i + chunk_size]) for i in range(0, len(output), chunk_size)]
                
                print(f"Processing {len(chunks)} chunks...")
                
                summaries = []
                for index, chunk in enumerate(chunks):
                    print(f"Processing chunk {index+1}/{len(chunks)}...")
                    response = await generate_ai_response(f"Summarize: {chunk}")
                    if model_type == 'llama':
                        summary = response.data.chat_response.choices[0].message.content[0].text
                    elif model_type == 'cohere':
                        summary = response.data.chat_response.text
                    else:
                        summary = ""
                    summaries.append(summary)
                    
                final_summary = ' '.join(summaries)
                buidJSON = {"msgType": "summary", "data": final_summary}
                await websocket.send(json.dumps(buidJSON))
    except websockets.exceptions.ConnectionClosedOK as e:
        print(f"Connection closed: {e}")
        
async def start_server():
    async with websockets.serve(handle_websocket, "localhost", 1986, max_size=200000000):
        await asyncio.Future()

asyncio.run(start_server())