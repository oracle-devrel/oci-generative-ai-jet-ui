from termcolor import colored

from agent_reasoning.agents.tot import ToTAgent


def test_tot():
    print(colored("=== Testing ToTAgent (Tree of Thoughts) ===", "magenta", attrs=["bold"]))
    agent = ToTAgent()
    agent.depth = 2  # Short depth for quick test
    agent.width = 2  # Narrow width for quick test

    # A problem requiring multiple steps (Game of 24 var)
    query = "Use the numbers 4, 5, 8, 2 to get 24. support +, -, *, /."

    result = agent.run(query)

    print("\n" + colored("Final Result:", "yellow"))
    print(result)


if __name__ == "__main__":
    test_tot()
