import re
from collections import Counter

from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import StreamEvent, TaskStatus, VotingSample


class ConsistencyAgent(BaseAgent):
    def __init__(self, model="gemma3:270m", samples=5, **kwargs):
        super().__init__(model, **kwargs)
        self.name = "ConsistencyAgent"
        self.color = "cyan"
        self.samples = samples

    def run(self, query):
        response = ""
        for chunk in self.stream(query):
            response += chunk
        return response

    def stream(self, query):
        """Yield text chunks for terminal streaming."""
        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data
            elif event.event_type == "sample":
                sample = event.data
                if sample.status == TaskStatus.COMPLETED and not event.is_update:
                    yield f"\n   -> *Extracted Answer: {sample.answer}*\n"

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(
            event_type="text",
            data=f"Processing query via Self-Consistency (k={self.samples}): {query}\n",
        )

        samples = []

        for i in range(self.samples):
            if not self._check_budget():
                yield StreamEvent(event_type="text", data=f"\n{self._budget_exceeded_msg}\n")
                break

            sample = VotingSample(id=i + 1, status=TaskStatus.RUNNING)
            samples.append(sample)
            yield StreamEvent(event_type="sample", data=sample)

            yield StreamEvent(event_type="text", data=f"\n**[Path {i + 1}/{self.samples}]**\n")

            prompt = (
                f"Question: {query}\nThink step-by-step to answer "
                "this question. End your answer with 'Final Answer: <answer>'."
            )

            trace_content = ""
            for chunk in self.client.generate(prompt, temperature=0.7, stream=True):
                trace_content += chunk
                sample.reasoning = trace_content
                yield StreamEvent(event_type="sample", data=sample, is_update=True)
                yield StreamEvent(event_type="text", data=chunk)

            # Extract Final Answer
            match = re.search(r"Final Answer:\s*(.*)", trace_content, re.IGNORECASE)
            final_ans = match.group(1).strip() if match else "Unknown"

            sample.answer = final_ans
            sample.status = TaskStatus.COMPLETED
            yield StreamEvent(event_type="sample", data=sample, is_update=True)

        # Majority Voting
        answers = [s.answer for s in samples if s.answer is not None]
        if not answers:
            yield StreamEvent(event_type="final", data="No answers generated (budget exceeded)")
            return
        counter = Counter(answers)
        best_answer, count = counter.most_common(1)[0]

        # Mark winners
        for sample in samples:
            sample.votes = counter[sample.answer]
            sample.is_winner = sample.answer == best_answer
            yield StreamEvent(event_type="sample", data=sample, is_update=True)

        yield StreamEvent(event_type="voting_complete", data=True)

        yield StreamEvent(event_type="text", data="\n---\n")
        yield StreamEvent(
            event_type="text",
            data=f"**Majority Logic:** {best_answer} ({count}/{self.samples} votes)\n",
        )
        yield StreamEvent(event_type="text", data="\n**Final Consolidated Answer:**\n")
        yield StreamEvent(event_type="text", data=best_answer)
        yield StreamEvent(event_type="text", data="\n")

        yield StreamEvent(event_type="final", data=best_answer)
