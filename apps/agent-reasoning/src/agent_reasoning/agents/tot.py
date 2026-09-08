import re

from termcolor import colored

from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import StreamEvent, TreeNode


class ToTAgent(BaseAgent):
    def __init__(self, model="gemma3:270m", **kwargs):
        super().__init__(model, **kwargs)
        self.name = "ToTAgent"
        self.color = "magenta"
        self.width = 2
        self.depth = 3

    def run(self, query):
        self.log_thought(f"Processing query via Tree of Thoughts (BFS): {query}")
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
            elif event.event_type == "node":
                node = event.data
                score_str = f" (score: {node.score:.2f})" if node.score else ""
                best = " ★" if node.is_best else ""
                yield f"\n  Branch {node.id}{score_str}{best}: {node.content[:100]}...\n"
            elif event.event_type == "final":
                yield f"\n{event.data}"

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(
            event_type="text",
            data=f"Thinking via Tree of Thoughts (Depth={self.depth}, Width={self.width})...\n",
        )

        current_thoughts = [("", None)]  # (thought_path, parent_id)
        node_counter = 0
        all_nodes = {}

        for step in range(self.depth):
            if not self._check_budget():
                yield StreamEvent(event_type="text", data=f"\n{self._budget_exceeded_msg}\n")
                break

            yield StreamEvent(
                event_type="text", data=f"\n[Step {step + 1}/{self.depth} - Exploring branches]\n"
            )

            candidates = []

            # 1. Generate Candidates
            for thought_path, parent_id in current_thoughts:
                if not self._check_budget():
                    yield StreamEvent(event_type="text", data=f"\n{self._budget_exceeded_msg}\n")
                    break

                prompt = (
                    f"Problem: {query}\nCurrent reasoning path:\n{thought_path}\n\n"
                    f"Provide {self.width} distinct possible next steps or continuations "
                    "to solve this problem. Label them Option 1, Option 2, etc."
                )

                response = ""
                for chunk in self.client.generate(prompt, stream=False):
                    response += chunk

                options = [opt for opt in response.split("Option ") if opt.strip()]
                if not options:
                    options = [response]
                options = options[: self.width]

                for i, opt in enumerate(options):
                    node_counter += 1
                    col = (node_counter - 1) % self.width + 1
                    row = chr(65 + (node_counter - 1) // self.width)
                    node_id = f"{row}{col}" if step > 0 else chr(65 + i)
                    new_thought = thought_path + "\n" + opt.strip()
                    candidates.append((new_thought, node_id, parent_id, opt.strip()))

            # 2. Evaluate Candidates
            scored_candidates = []
            for thought_path, node_id, parent_id, content in candidates:
                if not self._check_budget():
                    yield StreamEvent(event_type="text", data=f"\n{self._budget_exceeded_msg}\n")
                    break

                eval_prompt = (
                    f"Problem: {query}\nProposed Reasoning Path:\n{thought_path}\n\n"
                    "Rate this reasoning path from 0.0 to 1.0 based on correctness "
                    "and promise. Output ONLY the number."
                )

                score_str = ""
                for chunk in self.client.generate(eval_prompt, stream=False):
                    score_str += chunk

                try:
                    match = re.search(r"Score:\s*(0\.\d+|1\.0|0|1)", score_str, re.IGNORECASE)
                    if not match:
                        match = re.search(r"\b(0\.\d+|1\.0|0|1)\b", score_str)
                    score = float(match.group(1)) if match else 0.1
                except Exception:
                    score = 0.1

                node = TreeNode(
                    id=node_id, depth=step + 1, content=content, score=score, parent_id=parent_id
                )
                all_nodes[node_id] = node
                yield StreamEvent(event_type="node", data=node)

                scored_candidates.append((score, thought_path, node_id, content))

            # 3. Prune - keep top width
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            kept = scored_candidates[: self.width]
            pruned = scored_candidates[self.width :]

            # Mark pruned nodes
            for _, _, node_id, _ in pruned:
                if node_id in all_nodes:
                    all_nodes[node_id].is_pruned = True
                    yield StreamEvent(event_type="node", data=all_nodes[node_id], is_update=True)

            current_thoughts = [(path, nid) for _, path, nid, _ in kept]

        # Mark best path
        if current_thoughts:
            best_path, best_id = current_thoughts[0]
            if best_id in all_nodes:
                all_nodes[best_id].is_best = True
                yield StreamEvent(event_type="node", data=all_nodes[best_id], is_update=True)
        else:
            best_path = "No valid path found."

        yield StreamEvent(
            event_type="text", data="\n[Best Logic Trace selected. Generating Final Answer]\n"
        )

        final_prompt = (
            f"Problem: {query}\n\nReasoning Trace:\n{best_path}\n\n"
            "Instruction: Based on the reasoning above, provide a comprehensive "
            "and detailed final answer to the problem."
        )
        system_msg = (
            "You are a logic engine. You provide detailed, academic answers based on "
            "reasoning traces. Do not use conversational fillers like 'Okay' or 'Sure'."
        )

        final_response = ""
        if not self._check_budget():
            yield StreamEvent(event_type="text", data=f"\n{self._budget_exceeded_msg}\n")
            yield StreamEvent(event_type="final", data=best_path)
            return

        for chunk in self.client.generate(final_prompt, system=system_msg):
            final_response += chunk
            yield StreamEvent(event_type="text", data=chunk)

        yield StreamEvent(event_type="final", data=final_response)
