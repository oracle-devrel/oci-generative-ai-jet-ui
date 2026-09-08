import os
import sys

# Adjust path to include src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_reasoning.agents.recursive import RecursiveAgent


def test_recursive_agent():
    print("Testing RecursiveAgent...")
    # Use a dummy model or the real one.
    # Since we are running locally, we assume the model 'gemma3:270m' is available via Ollama.
    agent = RecursiveAgent(model="gemma3:270m")

    # Task that requires coding
    query = "Here is a list of numbers: 10, 25, 40, 5, 100. Write a python script to calculate the average and store it in FINAL_ANSWER."

    print(f"Query: {query}")
    print("-" * 50)

    result = agent.run(query)

    print("-" * 50)
    print("Final Result:", result)

    if "36" in str(result) or "36.0" in str(result):
        print("SUCCESS: Average seems correct (36).")
    else:
        print("WARNING: Result might be incorrect, check output.")


if __name__ == "__main__":
    test_recursive_agent()
