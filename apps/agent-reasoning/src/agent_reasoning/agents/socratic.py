from termcolor import colored

from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import SocraticExchange, StreamEvent


class SocraticAgent(BaseAgent):
    """Socratic method: progressive questioning to narrow solution space."""

    def __init__(self, model="gemma3:270m", max_questions=5, **kwargs):
        super().__init__(model, **kwargs)
        self.name = "SocraticAgent"
        self.color = "cyan"
        self.max_questions = max_questions

    def run(self, query):
        self.log_thought(f"Processing query with Socratic Method: {query}")
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
        yield StreamEvent(
            event_type="text",
            data=f"Socratic Method ({self.max_questions} questions)...\n",
        )

        qa_chain = []

        for q_num in range(1, self.max_questions + 1):
            exchange = SocraticExchange(question_num=q_num)
            yield StreamEvent(event_type="socratic", data=exchange)

            # Generate clarifying question
            yield StreamEvent(
                event_type="text",
                data=f"\n--- Question {q_num}/{self.max_questions} ---\n",
            )

            qa_context = "\n".join(
                [f"Q{i + 1}: {qa['q']}\nA{i + 1}: {qa['a']}" for i, qa in enumerate(qa_chain)]
            )

            question_prompt = (
                f"You are using the Socratic method to systematically answer: {query}\n\n"
                f"Questions asked so far:\n{qa_context if qa_context else 'None yet.'}\n\n"
                "Generate the next clarifying question that would most help "
                "narrow down the answer. "
                f"The question should probe a key assumption, definition, or sub-problem. "
                f"Output ONLY the question."
            )

            question = ""
            yield StreamEvent(event_type="text", data="Q: ")
            for chunk in self.client.generate(question_prompt, stream=True):
                question += chunk
                exchange.question = question
                yield StreamEvent(event_type="socratic", data=exchange, is_update=True)
                yield StreamEvent(event_type="text", data=chunk)

            # Self-answer the question
            yield StreamEvent(event_type="text", data="\nA: ")
            answer_prompt = (
                f"Original question: {query}\n"
                f"Sub-question to answer: {question}\n"
                f"Context from previous Q&A:\n{qa_context if qa_context else 'None.'}\n\n"
                f"Answer this sub-question thoroughly but concisely."
            )

            answer = ""
            for chunk in self.client.generate(answer_prompt, stream=True):
                answer += chunk
                exchange.answer = answer
                yield StreamEvent(event_type="socratic", data=exchange, is_update=True)
                yield StreamEvent(event_type="text", data=chunk)

            # What does this narrow down?
            narrowing_prompt = (
                f"Given Q: {question}\nA: {answer}\n\n"
                f"In one sentence, what does this narrow down about the original question: {query}?"
            )
            narrowing = ""
            for chunk in self.client.generate(narrowing_prompt, stream=False):
                narrowing += chunk
            exchange.narrows_to = narrowing.strip()
            yield StreamEvent(event_type="socratic", data=exchange, is_update=True)
            yield StreamEvent(
                event_type="text",
                data=f"\n[Narrows to: {narrowing.strip()}]\n",
            )

            qa_chain.append(
                {
                    "q": question.strip(),
                    "a": answer.strip(),
                    "narrows": narrowing.strip(),
                }
            )

        # Final synthesis
        yield StreamEvent(event_type="text", data="\n--- Synthesis ---\n")
        synthesis_exchange = SocraticExchange(
            question_num=self.max_questions + 1, is_final_synthesis=True
        )
        yield StreamEvent(event_type="socratic", data=synthesis_exchange)

        qa_summary = "\n".join(
            [
                f"Q{i + 1}: {qa['q']}\nA{i + 1}: {qa['a']}\nInsight: {qa['narrows']}"
                for i, qa in enumerate(qa_chain)
            ]
        )

        synthesis_prompt = (
            f"Original question: {query}\n\n"
            f"Through Socratic questioning, we established:\n{qa_summary}\n\n"
            f"Now synthesize a comprehensive final answer drawing on all insights above."
        )

        final_answer = ""
        for chunk in self.client.generate(synthesis_prompt, stream=True):
            final_answer += chunk
            synthesis_exchange.answer = final_answer
            yield StreamEvent(event_type="socratic", data=synthesis_exchange, is_update=True)
            yield StreamEvent(event_type="text", data=chunk)

        yield StreamEvent(event_type="final", data=final_answer)
