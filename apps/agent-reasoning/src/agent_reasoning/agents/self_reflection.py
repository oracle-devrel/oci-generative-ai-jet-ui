from termcolor import colored

from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import ReflectionIteration, StreamEvent


class SelfReflectionAgent(BaseAgent):
    def __init__(self, model="gemma3:270m", **kwargs):
        super().__init__(model, **kwargs)
        self.name = "SelfReflectionAgent"
        self.color = "green"

    def run(self, query):
        self.log_thought(f"Processing query with Self-Reflection: {query}")
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
            elif event.event_type == "iteration":
                iteration = event.data
                if iteration.is_correct:
                    yield colored("\n[Critique passed. Answer is correct.]\n", "green")

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        max_turns = 5
        current_answer = ""

        yield StreamEvent(event_type="query", data=query)

        # 1. Initial Attempt
        yield StreamEvent(event_type="text", data="[Drafting initial response...]\n")
        initial_prompt = f"Answer the following question: {query}"

        iteration = ReflectionIteration(iteration=1, draft="")
        yield StreamEvent(event_type="iteration", data=iteration)
        yield StreamEvent(event_type="phase", data="draft")

        yield StreamEvent(event_type="text", data="Initial Draft: ")
        for chunk in self.client.generate(initial_prompt):
            current_answer += chunk
            iteration.draft = current_answer
            yield StreamEvent(event_type="iteration", data=iteration, is_update=True)
            yield StreamEvent(event_type="text", data=chunk)
        yield StreamEvent(event_type="text", data="\n\n")

        # 2. Reflection Loop
        for turn in range(max_turns):
            yield StreamEvent(
                event_type="text", data=f"\n[Reflection Turn {turn + 1}/{max_turns}]\n"
            )

            # Create new iteration for turns > 0
            if turn > 0:
                iteration = ReflectionIteration(iteration=turn + 1, draft=current_answer)
                yield StreamEvent(event_type="iteration", data=iteration)

            # Critique
            yield StreamEvent(event_type="phase", data="critique")
            critique_prompt = f"Review the following answer to the question: '{query}'.\nAnswer: '{current_answer}'.\nIf the answer is correct and complete, output ONLY 'CORRECT'. Otherwise, list the errors."
            critique = ""
            yield StreamEvent(event_type="text", data="Critique: ")
            for chunk in self.client.generate(critique_prompt):
                critique += chunk
                iteration.critique = critique
                yield StreamEvent(event_type="iteration", data=iteration, is_update=True)
                yield StreamEvent(event_type="text", data=chunk)
            yield StreamEvent(event_type="text", data="\n")

            if "CORRECT" in critique.upper() and len(critique) < 20:
                iteration.is_correct = True
                yield StreamEvent(event_type="iteration", data=iteration, is_update=True)
                break

            # Improvement
            yield StreamEvent(event_type="phase", data="improvement")
            yield StreamEvent(event_type="text", data="Refining Answer...\n")
            improvement_prompt = f"Original Question: {query}\nCurrent Answer: {current_answer}\nCritique: {critique}\n\nProvide the corrected final answer."

            new_answer = ""
            for chunk in self.client.generate(improvement_prompt):
                new_answer += chunk
                iteration.improvement = new_answer
                yield StreamEvent(event_type="iteration", data=iteration, is_update=True)
                yield StreamEvent(event_type="text", data=chunk)
            yield StreamEvent(event_type="text", data="\n")
            current_answer = new_answer

        yield StreamEvent(event_type="text", data=f"\nFinal Result: {current_answer}\n")
        yield StreamEvent(event_type="final", data=current_answer)
