import re

from termcolor import colored

from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import DebateRound, StreamEvent


class DebateAgent(BaseAgent):
    def __init__(self, model="gemma3:270m", rounds=3, **kwargs):
        super().__init__(model, **kwargs)
        self.name = "DebateAgent"
        self.color = "red"
        self.rounds = rounds

    def run(self, query):
        self.log_thought(f"Processing query with Adversarial Debate: {query}")
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
            elif event.event_type == "debate_round":
                rnd = event.data
                if rnd.winner and not event.is_update:
                    yield f"\n  [Round {rnd.round_num} -> {rnd.winner.upper()} wins]\n"

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(
            event_type="text",
            data=f"Processing query via Adversarial Debate ({self.rounds} rounds): {query}\n",
        )

        rounds_data = []

        for i in range(self.rounds):
            round_num = i + 1
            rnd = DebateRound(round_num=round_num)
            rounds_data.append(rnd)
            yield StreamEvent(event_type="debate_round", data=rnd)

            # --- PRO argument ---
            yield StreamEvent(
                event_type="text", data=f"\n**[Round {round_num}/{self.rounds} - PRO]**\n"
            )

            pro_context = ""
            if i > 0:
                prev = rounds_data[i - 1]
                pro_context = (
                    f"\nPrevious round PRO argued: {prev.pro_argument}"
                    f"\nPrevious round CON argued: {prev.con_argument}"
                    f"\nJudge said: {prev.judge_commentary}"
                    f"\nBuild on the strongest PRO points and "
                    f"counter the CON arguments.\n"
                )

            pro_prompt = (
                f"You are a debater arguing IN FAVOR of the following position.\n"
                f"Question: {query}\n"
                f"{pro_context}"
                f"Present a strong, concise argument supporting this position. "
                f"Focus on evidence, logic, and persuasion."
            )

            pro_argument = ""
            for chunk in self.client.generate(pro_prompt):
                pro_argument += chunk
                rnd.pro_argument = pro_argument
                yield StreamEvent(event_type="debate_round", data=rnd, is_update=True)
                yield StreamEvent(event_type="text", data=chunk)
            yield StreamEvent(event_type="text", data="\n")

            # --- CON argument ---
            yield StreamEvent(
                event_type="text", data=f"\n**[Round {round_num}/{self.rounds} - CON]**\n"
            )

            con_context = ""
            if i > 0:
                prev = rounds_data[i - 1]
                con_context = (
                    f"\nPrevious round PRO argued: {prev.pro_argument}"
                    f"\nPrevious round CON argued: {prev.con_argument}"
                    f"\nJudge said: {prev.judge_commentary}"
                    f"\nBuild on the strongest CON points and "
                    f"counter the PRO arguments.\n"
                )

            con_prompt = (
                f"You are a debater arguing AGAINST the following position.\n"
                f"Question: {query}\n"
                f"The PRO side argued: {pro_argument}\n"
                f"{con_context}"
                f"Present a strong, concise rebuttal and counter-argument. "
                f"Focus on weaknesses in the PRO argument and provide alternative evidence."
            )

            con_argument = ""
            for chunk in self.client.generate(con_prompt):
                con_argument += chunk
                rnd.con_argument = con_argument
                yield StreamEvent(event_type="debate_round", data=rnd, is_update=True)
                yield StreamEvent(event_type="text", data=chunk)
            yield StreamEvent(event_type="text", data="\n")

            # --- Judge evaluation (non-streaming) ---
            yield StreamEvent(
                event_type="text", data=f"\n**[Round {round_num}/{self.rounds} - JUDGE]**\n"
            )

            judge_prompt = (
                f"You are an impartial judge evaluating a debate.\n"
                f"Question: {query}\n\n"
                f"PRO argument:\n{pro_argument}\n\n"
                f"CON argument:\n{con_argument}\n\n"
                f"Score each argument from 0 to 10 and declare a winner.\n"
                f"You MUST respond in exactly this format:\n"
                f"PRO_SCORE: <number>\n"
                f"CON_SCORE: <number>\n"
                f"WINNER: <PRO or CON>\n"
                f"COMMENTARY: <brief explanation>"
            )

            judge_response = ""
            for chunk in self.client.generate(judge_prompt, stream=False):
                judge_response += chunk

            # Parse judge scores with regex
            pro_score_match = re.search(r"PRO_SCORE:\s*(\d+(?:\.\d+)?)", judge_response)
            con_score_match = re.search(r"CON_SCORE:\s*(\d+(?:\.\d+)?)", judge_response)
            winner_match = re.search(r"WINNER:\s*(PRO|CON)", judge_response, re.IGNORECASE)
            commentary_match = re.search(r"COMMENTARY:\s*(.*)", judge_response, re.DOTALL)

            rnd.judge_score_pro = float(pro_score_match.group(1)) if pro_score_match else 5.0
            rnd.judge_score_con = float(con_score_match.group(1)) if con_score_match else 5.0
            rnd.judge_commentary = (
                commentary_match.group(1).strip() if commentary_match else judge_response.strip()
            )

            if winner_match:
                rnd.winner = winner_match.group(1).lower()
            else:
                # Fallback: higher score wins
                rnd.winner = "pro" if rnd.judge_score_pro >= rnd.judge_score_con else "con"

            yield StreamEvent(event_type="debate_round", data=rnd, is_update=True)

            judge_summary = (
                f"PRO: {rnd.judge_score_pro}/10 | CON: {rnd.judge_score_con}/10 | "
                f"Winner: {rnd.winner.upper()}\n{rnd.judge_commentary}\n"
            )
            yield StreamEvent(event_type="text", data=judge_summary)

            # Emit the finalized round (non-update) to signal round completion
            yield StreamEvent(event_type="debate_round", data=rnd)

        # --- Final synthesis ---
        yield StreamEvent(event_type="text", data="\n---\n**[Final Synthesis]**\n")

        rounds_summary = ""
        for rnd in rounds_data:
            rounds_summary += (
                f"Round {rnd.round_num}:\n"
                f"  PRO ({rnd.judge_score_pro}/10): {rnd.pro_argument}\n"
                f"  CON ({rnd.judge_score_con}/10): {rnd.con_argument}\n"
                f"  Judge: {rnd.judge_commentary}\n\n"
            )

        synthesis_prompt = (
            f"You have observed an adversarial debate on the following question:\n"
            f"{query}\n\n"
            f"Here is a summary of all rounds:\n{rounds_summary}\n"
            f"Now provide a final, balanced answer that incorporates the strongest "
            f"arguments from both sides. Acknowledge valid points from each perspective "
            f"and arrive at a nuanced conclusion."
        )

        final_answer = ""
        for chunk in self.client.generate(synthesis_prompt):
            final_answer += chunk
            yield StreamEvent(event_type="text", data=chunk)
        yield StreamEvent(event_type="text", data="\n")

        yield StreamEvent(event_type="final", data=final_answer)
