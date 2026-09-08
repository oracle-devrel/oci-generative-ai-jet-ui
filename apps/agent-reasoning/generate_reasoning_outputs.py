import os
import sys

# Ensure we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agent_reasoning.interceptor import AGENT_MAP

# Configuration
QUERY = "What is the meaning of life?"
MODEL_BASE = "gemma3:latest"
OUTPUT_FILE = "data/meaning_of_life_reasoning.txt"

# Strategies to run
STRATEGIES = ["consistency"]


def main():
    print(f"Generating reasoning outputs for: '{QUERY}'")
    print(f"Model: {MODEL_BASE}")
    print(f"Output File: {OUTPUT_FILE}")

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for strategy in STRATEGIES:
            print(f"Running strategy: {strategy}...")

            # Formatted Headers matching user request
            f.write(f"Query: {QUERY}\n")
            f.write(f"Using model: {MODEL_BASE}+{strategy}\n")
            f.write(f"--- {strategy.upper()} Thinking ---\n")

            try:
                # Instantiate Agent
                agent_class = AGENT_MAP.get(strategy)
                if not agent_class:
                    f.write(f"Error: Strategy '{strategy}' not found.\n")
                    continue

                agent = agent_class(model=MODEL_BASE)

                # Run Stream and Capture
                if hasattr(agent, "stream"):
                    for chunk in agent.stream(QUERY):
                        # Write raw chunk to file
                        f.write(chunk)
                else:
                    # Fallback if no stream (shouldn't happen for valid agents)
                    res = agent.run(QUERY)
                    f.write(res)

            except Exception as e:
                f.write(f"\n[ERROR occurred during execution: {e}]\n")

            f.write("\n\n" + "=" * 80 + "\n\n")

    print(f"Completed. Output saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
