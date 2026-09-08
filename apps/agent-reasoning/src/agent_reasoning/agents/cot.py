import re

from termcolor import colored

from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import ChainStep, StreamEvent


class CoTAgent(BaseAgent):
    def __init__(self, model="gemma3:270m", **kwargs):
        super().__init__(model, **kwargs)
        self.name = "CoTAgent"
        self.color = "blue"

    def run(self, query):
        self.log_thought(f"Processing query with Chain-of-Thought: {query}")
        print(colored("Reasoning: ", self.color), end="", flush=True)
        full_response = ""
        for chunk in self.stream(query):
            print(colored(chunk, self.color), end="", flush=True)
            full_response += chunk
        print()
        return full_response

    def stream(self, query):
        """Yield text chunks for terminal streaming."""
        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)

        # Injecting CoT instruction
        prompt = (
            f"Question: {query}\n\n"
            "Instruction: Think step-by-step to answer the question. "
            "Break down the reasoning process clearly. "
            "Number each step (Step 1, Step 2, etc.). "
            "Provide a detailed final answer."
        )

        full_response = ""
        current_step = ChainStep(step=1, content="")
        yield StreamEvent(event_type="chain_step", data=current_step)
        yield StreamEvent(event_type="text", data="Reasoning:\n")

        # Stream the thought process
        for chunk in self.client.generate(prompt):
            full_response += chunk
            yield StreamEvent(event_type="text", data=chunk)

            # Check if we've started a new step (e.g., "Step 2:", "2.", "Second,")
            step_pattern = r"(?:Step\s*(\d+)|^(\d+)\.|^\*\*Step\s*(\d+))"
            matches = list(re.finditer(step_pattern, full_response, re.MULTILINE | re.IGNORECASE))

            if matches:
                last_match = matches[-1]
                step_num = int(last_match.group(1) or last_match.group(2) or last_match.group(3))

                if step_num > current_step.step:
                    # Complete the previous step
                    current_step.is_final = False
                    yield StreamEvent(event_type="chain_step", data=current_step, is_update=True)

                    # Start new step
                    current_step = ChainStep(step=step_num, content="")
                    yield StreamEvent(event_type="chain_step", data=current_step)

            # Update current step content
            current_step.content = full_response
            yield StreamEvent(event_type="chain_step", data=current_step, is_update=True)

        # Mark final step
        current_step.is_final = True
        current_step.total_steps = current_step.step
        yield StreamEvent(event_type="chain_step", data=current_step, is_update=True)

        yield StreamEvent(event_type="final", data=full_response)
