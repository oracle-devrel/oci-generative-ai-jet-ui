from termcolor import colored

from agent_reasoning.agents.consistency import ConsistencyAgent
from agent_reasoning.agents.decomposed import DecomposedAgent
from agent_reasoning.agents.least_to_most import LeastToMostAgent
from agent_reasoning.agents.react import ReActAgent
from agent_reasoning.agents.tot import ToTAgent


def run_benchmark():
    tasks = [
        (
            "Philosophy (Self-Consistency)",
            "What is the meaning of life? Answer with biological and philosophical perspectives.",
        ),
        (
            "Logic Riddle (ToT)",
            "I have a 3-gallon jug and a 5-gallon jug."
            " How can I measure exactly 4 gallons of water?",
        ),
        (
            "Planning (Decomposed)",
            "Plan a detailed 3-day itinerary for Tokyo"
            " for a history buff who loves samurais and tea.",
        ),
        (
            "Complex Physics (Least-to-Most)",
            "A train travels at 0.6c for 5 years (train time)."
            " How much time has passed on Earth? Explain the steps.",
        ),
        ("Tool Use (ReAct)", "Who is the current CEO of Google? Calculate the square root of 144."),
    ]

    print(colored("=== Agent Reasoning Benchmark ===", "green", attrs=["bold"]))
    print("Model: gemma3:270m (via Ollama)\n")

    for category, query in tasks:
        print(colored(f"\n\n>>> Task [{category}]: {query}", "white", attrs=["bold", "underline"]))

        # Select agents based on task type to show off strengths
        if "Philosophy" in category:
            current_agents = [
                ConsistencyAgent(samples=3)
            ]  # Use Consistency for diverse thoughts + voting
        elif "Logic" in category:
            current_agents = [ToTAgent()]
        elif "Planning" in category:
            current_agents = [DecomposedAgent()]  # Decomposed is great for itineraries
        elif "Complex" in category:
            current_agents = [LeastToMostAgent()]
        elif "Tool" in category:
            # ReAct is specific for tools
            current_agents = [ReActAgent()]

        for agent in current_agents:
            print(colored(f"\n--- {agent.name} ---", "yellow"))
            try:
                # Use run() which uses stream() internally now and handles printing
                agent.run(query)
            except Exception as e:
                print(colored(f"Error: {e}", "red"))


if __name__ == "__main__":
    run_benchmark()
