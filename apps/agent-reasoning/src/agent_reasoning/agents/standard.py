from termcolor import colored

from agent_reasoning.agents.base import BaseAgent


class StandardAgent(BaseAgent):
    def __init__(self, model="gemma3:270m", **kwargs):
        super().__init__(model, **kwargs)
        self.name = "StandardAgent"
        self.color = "cyan"

    def run(self, query):
        self.log_thought(f"Processing query: {query}")
        print(colored("Answer: ", self.color), end="", flush=True)
        full_response = ""
        for chunk in self.stream(query):
            print(colored(chunk, self.color), end="", flush=True)
            full_response += chunk
        print()
        return full_response

    def stream(self, query):
        prompt = f"Question: {query}\n\nAnswer:"
        for chunk in self.client.generate(prompt):
            yield chunk
