"""OCI Responses and Conversations API client and model message handling."""

import json
import re
import uuid

import httpx
from oci_genai_auth import OciSessionAuth
from openai import OpenAI
from IPython.display import Markdown, display

from demo_utils import ModelOutputError, show_message


class Inferencing:
    """OCI Responses client, managed conversation and message parsing."""

    def __init__(self, settings):
        self.settings = settings
        self.auth = OciSessionAuth(profile_name=settings["profile"])
        self.run = {"generated_files": {}}
        endpoint = f"https://inference.generativeai.{settings['region']}.oci.oraclecloud.com"
        self.client = OpenAI(
            base_url=f"{endpoint}/openai/v1", api_key="not-used",
            project=settings["project_id"], http_client=httpx.Client(auth=self.auth),
            max_retries=0, timeout=180,
        )

    def create_conversation(self, *, instructions, tools):
        conversation = self.client.conversations.create(metadata={
            "name": f"sandboxes-demo-conversation-{uuid.uuid4().hex[:12]}",
        })
        self.run.clear()
        self.run.update(conversation_id=conversation.id, generated_files={})
        self.instructions = instructions
        self.tools = tools
        return self

    def send(self, message):
        request = {
            "model": self.settings["model_id"], "conversation": self.run["conversation_id"],
            "instructions": self.instructions(),
            "tools": self.tools,
            "input": message, "tool_choice": "auto", "reasoning": {"effort": "medium"},
            "max_output_tokens": 8000,
        }
        show_message("Sent to model", request)
        response = self.client.responses.create(**request)
        show_message("Received from model", response.model_dump(mode="json"))
        if response.status != "completed":
            raise RuntimeError(f"Response ended with status {response.status}: {response.error or response.incomplete_details}")
        return response

    def requests_execution(self, response):
        return any(item.type == "function_call" for item in response.output)

    def get_tool_call(self, response):
        calls = [item for item in response.output if item.type == "function_call"]
        if len(calls) != 1:
            raise ModelOutputError("Expected one tool request at a time.")
        try:
            return calls[0].name, json.loads(calls[0].arguments)
        except json.JSONDecodeError as error:
            raise ModelOutputError(str(error)) from error

    def send_result(self, response, result):
        messages = [{"type": "function_call_output", "call_id": call.call_id,
                     "output": json.dumps(result, allow_nan=False)}
                    for call in response.output if call.type == "function_call"]
        return self.send(messages)

    def show_answer(self, response):
        """Display the final explanation."""
        if not response.output_text.strip():
            raise ValueError("The model returned no explanation.")
        display(Markdown(re.sub(r"(?<!\\)\$", r"\\$", response.output_text)))
