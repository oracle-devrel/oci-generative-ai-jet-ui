from termcolor import colored

from agent_reasoning.agents.consistency import ConsistencyAgent


def test_consistency():
    print(colored("=== Testing ConsistencyAgent ===", "cyan", attrs=["bold"]))
    agent = ConsistencyAgent(samples=3)  # Use 3 for speed

    # A problem that might benefit from voting (or at least show diversity)
    query = "If I have 30 apples and eat 2 per day, but every 3rd day I buy 1 more, how many do I have after 5 days?"

    # Run
    result = agent.run(query)

    print("\n" + colored("Final Result:", "yellow"))
    print(result)


if __name__ == "__main__":
    test_consistency()
