import re

from termcolor import colored

from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import RefinementIteration, StreamEvent


class RefinementLoopAgent(BaseAgent):
    """
    Iterative Refinement Agent with score-based termination.

    Implements the refinement loop pattern:
    1. Generator creates initial draft
    2. Critic evaluates with a score (0.0-1.0) and provides feedback
    3. Refiner improves draft based on feedback
    4. Loop until score >= threshold

    Reference: Based on iterative refinement patterns for reliable generation.
    """

    def __init__(self, model="gemma3:270m", score_threshold=0.9, max_iterations=10, **kwargs):
        super().__init__(model, **kwargs)
        self.name = "RefinementLoopAgent"
        self.color = "yellow"
        self.score_threshold = score_threshold
        self.max_iterations = max_iterations

    def run(self, query):
        self.log_thought(f"Processing query with Refinement Loop: {query}")
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
            elif event.event_type == "refinement":
                iteration = event.data
                if iteration.is_accepted:
                    yield colored(
                        f"\n[Score {iteration.score:.2f} >= {self.score_threshold} - ACCEPTED]\n",
                        "green",
                    )

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(
            event_type="text",
            data=f"Processing via Refinement Loop (threshold={self.score_threshold})...\n",
        )

        # 1. GENERATE: Initial draft
        yield StreamEvent(event_type="text", data="\n[GENERATOR] Creating initial draft...\n")

        generator_prompt = (
            f"You are a helpful assistant. Answer the following "
            f"question thoroughly and accurately.\n\n"
            f"Question: {query}\n\n"
            f"Provide a comprehensive answer:"
        )

        draft = ""
        iteration = RefinementIteration(iteration=1, draft="")
        yield StreamEvent(event_type="refinement", data=iteration)

        if not self._check_budget():
            yield StreamEvent(event_type="text", data=f"\n{self._budget_exceeded_msg}\n")
            yield StreamEvent(event_type="final", data="Budget exceeded before generation")
            return

        yield StreamEvent(event_type="text", data="Draft: ")
        for chunk in self.client.generate(generator_prompt):
            draft += chunk
            iteration.draft = draft
            yield StreamEvent(event_type="refinement", data=iteration, is_update=True)
            yield StreamEvent(event_type="text", data=chunk)
        yield StreamEvent(event_type="text", data="\n")

        # 2. CRITIQUE & REFINE Loop
        current_draft = draft

        for i in range(self.max_iterations):
            if not self._check_budget():
                yield StreamEvent(event_type="text", data=f"\n{self._budget_exceeded_msg}\n")
                break

            yield StreamEvent(
                event_type="text",
                data=f"\n[CRITIC] Evaluating draft (iteration {i + 1}/{self.max_iterations})...\n",
            )

            # Critic evaluates and provides score + feedback
            critic_prompt = (
                f"You are a strict quality evaluator. Evaluate "
                f"the following answer to the question.\n\n"
                f"Question: {query}\n\n"
                f"Answer to evaluate:\n{current_draft}\n\n"
                f"Instructions:\n"
                f"1. Assess the answer for accuracy, completeness, "
                f"clarity, and relevance.\n"
                f"2. Provide a quality score from 0.0 to 1.0 "
                f"(where 1.0 is perfect).\n"
                f"3. If the score is below 0.9, provide specific "
                f"feedback on what needs improvement.\n\n"
                f"Format your response EXACTLY as:\n"
                f"SCORE: [number between 0.0 and 1.0]\n"
                f"FEEDBACK: [specific improvement suggestions, or "
                f'"No improvements needed" if score >= 0.9]'
            )

            critique_response = ""
            yield StreamEvent(event_type="text", data="Critique: ")
            for chunk in self.client.generate(critic_prompt):
                critique_response += chunk
                yield StreamEvent(event_type="text", data=chunk)
            yield StreamEvent(event_type="text", data="\n")

            # Parse score and feedback
            score = self._extract_score(critique_response)
            feedback = self._extract_feedback(critique_response)

            iteration = RefinementIteration(
                iteration=i + 1,
                draft=current_draft,
                critique=critique_response,
                feedback=feedback,
                score=score,
            )

            yield StreamEvent(
                event_type="text",
                data=f"\n   -> Score: {score:.2f}, Threshold: {self.score_threshold}\n",
            )

            # Check if we've reached the threshold
            if score >= self.score_threshold:
                iteration.is_accepted = True
                yield StreamEvent(event_type="refinement", data=iteration)
                yield StreamEvent(
                    event_type="text",
                    data=colored(f"\n[ACCEPTED] Score {score:.2f} meets threshold.\n", "green"),
                )
                break

            yield StreamEvent(event_type="refinement", data=iteration)

            # 3. REFINE: Improve draft based on feedback
            if not self._check_budget():
                yield StreamEvent(event_type="text", data=f"\n{self._budget_exceeded_msg}\n")
                break

            yield StreamEvent(
                event_type="text", data="\n[REFINER] Improving draft based on feedback...\n"
            )

            refiner_prompt = (
                f"You are a skilled editor. Improve the following "
                f"answer based on the feedback provided.\n\n"
                f"Original Question: {query}\n\n"
                f"Current Draft:\n{current_draft}\n\n"
                f"Feedback to address:\n{feedback}\n\n"
                f"Instructions: Rewrite the answer to address ALL "
                f"the feedback points. Maintain accuracy while "
                f"improving quality.\n\n"
                f"Improved Answer:"
            )

            new_draft = ""
            yield StreamEvent(event_type="text", data="Refined Draft: ")
            for chunk in self.client.generate(refiner_prompt):
                new_draft += chunk
                yield StreamEvent(event_type="text", data=chunk)
            yield StreamEvent(event_type="text", data="\n")

            current_draft = new_draft

        else:
            # Max iterations reached without meeting threshold
            yield StreamEvent(
                event_type="text",
                data=colored(
                    f"\n[MAX ITERATIONS] Reached {self.max_iterations} "
                    f"iterations. Using best draft.\n",
                    "yellow",
                ),
            )

        yield StreamEvent(event_type="text", data="\n" + "=" * 50 + "\n")
        yield StreamEvent(event_type="text", data="FINAL RESULT:\n")
        yield StreamEvent(event_type="text", data=current_draft)
        yield StreamEvent(event_type="text", data="\n")

        yield StreamEvent(event_type="final", data=current_draft)

    def _extract_score(self, critique: str) -> float:
        """Extract numeric score from critique response."""
        # Try to find "SCORE: X.X" pattern
        match = re.search(r"SCORE:\s*(0?\.\d+|1\.0|1|0)", critique, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        # Fallback: look for any decimal number
        match = re.search(r"\b(0\.\d+|1\.0)\b", critique)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        # Default to low score if parsing fails
        return 0.5

    def _extract_feedback(self, critique: str) -> str:
        """Extract feedback from critique response."""
        # Try to find "FEEDBACK: ..." pattern
        match = re.search(r"FEEDBACK:\s*(.+)", critique, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

        # Fallback: return entire critique as feedback
        return critique
