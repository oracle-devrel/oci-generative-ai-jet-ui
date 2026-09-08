import math
import re

from termcolor import colored

from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import MCTSNode, StreamEvent


class MCTSAgent(BaseAgent):
    def __init__(self, model="gemma3:270m", **kwargs):
        super().__init__(model, **kwargs)
        self.name = "MCTSAgent"
        self.color = "blue"
        self.max_simulations = 20
        self.exploration_constant = 1.414
        self.max_children = 2

    def run(self, query):
        self.log_thought(f"Processing query via MCTS: {query}")
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
            elif event.event_type == "mcts_node":
                node = event.data
                win_rate = (
                    f" (wins/visits: {node.wins:.1f}/{node.visits})" if node.visits > 0 else ""
                )
                best = " *" if node.is_best else ""
                yield f"\n  Node {node.id}{win_rate}{best}: {node.content[:100]}...\n"
            elif event.event_type == "final":
                yield f"\n{event.data}"

    def _ucb1(self, wins, visits, parent_visits):
        """Upper Confidence Bound 1 formula for node selection."""
        if visits == 0:
            return float("inf")
        return (wins / visits) + self.exploration_constant * math.sqrt(
            math.log(parent_visits) / visits
        )

    def _select(self, tree, node_id):
        """Selection phase: traverse tree using UCB1 until we reach a leaf or expandable node."""
        current_id = node_id
        while True:
            children = tree[current_id]["children"]
            if not children:
                return current_id
            # If the node can still be expanded (fewer children than max), select it
            if len(children) < self.max_children:
                return current_id
            # Otherwise, pick the child with the highest UCB1 score
            parent_visits = tree[current_id]["node"].visits
            best_child = None
            best_score = -1.0
            for child_id in children:
                child_node = tree[child_id]["node"]
                score = self._ucb1(child_node.wins, child_node.visits, parent_visits)
                if score > best_score:
                    best_score = score
                    best_child = child_id
            current_id = best_child

    def _expand(self, tree, node_id, query, node_counter):
        """Expansion phase: generate a new child reasoning step via LLM."""
        parent_path = tree[node_id]["thought_path"]
        prompt = (
            f"Problem: {query}\n"
            f"Current reasoning path:\n{parent_path}\n\n"
            f"Provide one possible next reasoning step to advance toward solving this problem. "
            f"Be specific and concise."
        )

        response = ""
        for chunk in self.client.generate(prompt, stream=False, temperature=0.8):
            response += chunk

        if not response.strip():
            response = "Continue reasoning..."

        child_id = f"N{node_counter}"
        parent_depth = tree[node_id]["node"].depth
        child_path = parent_path + "\n" + response.strip()

        child_node = MCTSNode(
            id=child_id,
            depth=parent_depth + 1,
            content=response.strip(),
            parent_id=node_id,
        )

        tree[child_id] = {
            "node": child_node,
            "children": [],
            "thought_path": child_path,
        }
        tree[node_id]["children"].append(child_id)

        return child_id

    def _simulate(self, tree, node_id, query):
        """Simulation phase: evaluate the quality of the path from root to this node (0.0-1.0)."""
        thought_path = tree[node_id]["thought_path"]
        eval_prompt = (
            f"Problem: {query}\n"
            f"Proposed Reasoning Path:\n{thought_path}\n\n"
            f"Rate this reasoning path from 0.0 to 1.0 based on correctness and promise. "
            f"Output ONLY the number."
        )

        score_str = ""
        for chunk in self.client.generate(eval_prompt, stream=False):
            score_str += chunk

        try:
            match = re.search(r"Score:\s*(0\.\d+|1\.0|0|1)", score_str, re.IGNORECASE)
            if not match:
                match = re.search(r"\b(0\.\d+|1\.0|0|1)\b", score_str)
            score = float(match.group(1)) if match else 0.5
        except Exception:
            score = 0.5

        return score

    def _backpropagate(self, tree, node_id, score):
        """Backpropagation phase: update visits and wins from leaf to root."""
        current_id = node_id
        while current_id is not None:
            tree[current_id]["node"].visits += 1
            tree[current_id]["node"].wins += score
            current_id = tree[current_id]["node"].parent_id

    def _best_path(self, tree, root_id):
        """Follow highest win-rate children from root to build the best reasoning path."""
        path_ids = [root_id]
        current_id = root_id
        while tree[current_id]["children"]:
            children = tree[current_id]["children"]
            # Pick child with highest win rate (wins/visits)
            best_child = None
            best_rate = -1.0
            for child_id in children:
                child_node = tree[child_id]["node"]
                if child_node.visits > 0:
                    rate = child_node.wins / child_node.visits
                    if rate > best_rate:
                        best_rate = rate
                        best_child = child_id
                else:
                    # Unvisited child - skip
                    pass
            if best_child is None:
                break
            path_ids.append(best_child)
            current_id = best_child
        return path_ids

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(
            event_type="text",
            data=f"Thinking via MCTS (simulations={self.max_simulations}, "
            f"c={self.exploration_constant}, max_children={self.max_children})...\n",
        )

        # Initialize tree with root node
        root_id = "N0"
        root_node = MCTSNode(
            id=root_id,
            depth=0,
            content=query,
        )
        tree = {
            root_id: {
                "node": root_node,
                "children": [],
                "thought_path": query,
            }
        }
        node_counter = 1

        yield StreamEvent(event_type="mcts_node", data=root_node)

        # Run MCTS simulations
        for sim in range(self.max_simulations):
            yield StreamEvent(
                event_type="text", data=f"\n[Simulation {sim + 1}/{self.max_simulations}]\n"
            )

            # 1. Selection
            selected_id = self._select(tree, root_id)

            # 2. Expansion
            child_id = self._expand(tree, selected_id, query, node_counter)
            node_counter += 1

            child_node = tree[child_id]["node"]
            yield StreamEvent(event_type="mcts_node", data=child_node)

            # 3. Simulation (evaluate path quality)
            score = self._simulate(tree, child_id, query)
            child_node.score = score

            yield StreamEvent(event_type="text", data=f"  Simulation score: {score:.2f}\n")

            # 4. Backpropagation
            self._backpropagate(tree, child_id, score)

            # Emit updated node with visits/wins
            yield StreamEvent(event_type="mcts_node", data=child_node, is_update=True)

        # Find best path through the tree
        best_path_ids = self._best_path(tree, root_id)

        # Mark best path nodes
        for nid in best_path_ids:
            tree[nid]["node"].is_best = True
            yield StreamEvent(event_type="mcts_node", data=tree[nid]["node"], is_update=True)

        # Build the best reasoning trace
        if len(best_path_ids) > 1:
            best_thought_path = tree[best_path_ids[-1]]["thought_path"]
        else:
            best_thought_path = query

        yield StreamEvent(
            event_type="text", data="\n[Best path selected via MCTS. Generating Final Answer]\n"
        )

        # Generate final answer using the best reasoning path
        final_prompt = (
            f"Problem: {query}\n\n"
            f"Reasoning Trace:\n{best_thought_path}\n\n"
            f"Instruction: Based on the reasoning above, provide a comprehensive "
            f"and detailed final answer to the problem."
        )
        system_msg = (
            "You are a logic engine. You provide detailed, academic answers based on "
            "reasoning traces. Do not use conversational fillers like 'Okay' or 'Sure'."
        )

        final_response = ""
        for chunk in self.client.generate(final_prompt, system=system_msg):
            final_response += chunk
            yield StreamEvent(event_type="text", data=chunk)

        yield StreamEvent(event_type="final", data=final_response)
