from termcolor import colored

from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import AnalogyMapping, StreamEvent


class AnalogicalAgent(BaseAgent):
    """Analogical reasoning: solve problems by structural analogy."""

    def __init__(self, model="gemma3:270m", num_analogies=3, **kwargs):
        super().__init__(model, **kwargs)
        self.name = "AnalogicalAgent"
        self.color = "yellow"
        self.num_analogies = num_analogies

    def run(self, query):
        self.log_thought(f"Processing query with Analogical Reasoning: {query}")
        full_response = ""
        for chunk in self.stream(query):
            print(colored(chunk, self.color), end="", flush=True)
            full_response += chunk
        print()
        return full_response

    def stream(self, query):
        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data

    def stream_structured(self, query):
        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(event_type="text", data="Analogical Reasoning...\n")

        # Phase 1: Identify abstract structure
        mapping = AnalogyMapping(step=1, phase="identify")
        yield StreamEvent(event_type="analogy", data=mapping)
        yield StreamEvent(event_type="text", data="\n[Phase 1: Identifying problem structure]\n")

        structure_prompt = (
            "Analyze the abstract structure of this problem. "
            "What are the key entities, relationships, "
            f"and dynamics? Do NOT solve it yet.\n\n"
            f"Problem: {query}\n\n"
            "Output the abstract structure concisely."
        )
        structure = ""
        for chunk in self.client.generate(structure_prompt, stream=True):
            structure += chunk
            mapping.abstract_structure = structure
            mapping.target_domain = query[:100]
            yield StreamEvent(event_type="analogy", data=mapping, is_update=True)
            yield StreamEvent(event_type="text", data=chunk)

        # Phase 2: Generate analogies from different domains
        yield StreamEvent(
            event_type="text", data=f"\n\n[Phase 2: Generating {self.num_analogies} analogies]\n"
        )
        analogy_prompt = (
            f"The following problem has this abstract structure:\n"
            f"{structure}\n\n"
            f"Problem: {query}\n\n"
            f"Generate {self.num_analogies} analogous problems from "
            "DIFFERENT domains that share this "
            "same abstract structure. For each, explain the "
            "structural mapping.\n"
            "Format: ANALOGY N: <domain> - <problem description>\n"
            "MAPPING: <how elements correspond>"
        )
        analogies_text = ""
        for chunk in self.client.generate(analogy_prompt, stream=True):
            analogies_text += chunk
            yield StreamEvent(event_type="text", data=chunk)
        mapping.phase = "generate"
        mapping.source_domain = analogies_text[:200]
        yield StreamEvent(event_type="analogy", data=mapping, is_update=True)

        # Phase 3: Select best analogy and transfer solution
        yield StreamEvent(
            event_type="text", data="\n\n[Phase 3: Transferring solution from best analogy]\n"
        )
        select_prompt = (
            f"From these analogies:\n{analogies_text}\n\n"
            f"Select the ONE that best maps to the original problem:\n{query}\n\n"
            f"Explain which analogy you chose and why. Then show how the solution approach "
            f"from the analogous domain transfers to solve the original problem."
        )
        transfer = ""
        mapping.phase = "transfer"
        mapping.step = 3
        yield StreamEvent(event_type="analogy", data=mapping)
        for chunk in self.client.generate(select_prompt, stream=True):
            transfer += chunk
            mapping.solution_transfer = transfer
            mapping.mapping = transfer[:200]
            yield StreamEvent(event_type="analogy", data=mapping, is_update=True)
            yield StreamEvent(event_type="text", data=chunk)

        # Final synthesis
        yield StreamEvent(event_type="text", data="\n\n[Synthesizing final answer]\n")
        final_prompt = (
            f"Original problem: {query}\n\n"
            f"Solution approach transferred from analogy:\n"
            f"{transfer}\n\n"
            "Now provide the definitive answer to the original "
            "problem, applying the insights gained."
        )
        final_answer = ""
        for chunk in self.client.generate(final_prompt, stream=True):
            final_answer += chunk
            yield StreamEvent(event_type="text", data=chunk)
        yield StreamEvent(event_type="final", data=final_answer)
