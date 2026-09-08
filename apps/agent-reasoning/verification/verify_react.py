from termcolor import colored

from agent_reasoning.agents.react import ReActAgent


def test_react():
    print(colored("=== Testing ReActAgent (Reasoning + Acting) ===", "blue", attrs=["bold"]))
    agent = ReActAgent()

    # A question requiring outside knowledge (Web Search)
    query = "Use web_search to find the current CEO of Google."

    agent.run(query)

    print("\n[Done]")


if __name__ == "__main__":
    test_react()
