from termcolor import colored

from agent_reasoning.agents.self_reflection import SelfReflectionAgent


def test_reflexion():
    print(colored("=== Testing SelfReflectionAgent ===", "green", attrs=["bold"]))
    agent = SelfReflectionAgent()

    # A tricky question that might induce hallucinations or incomplete answers initially
    query = "What is the capital of the country that has the city Timbuktu?"
    # Timbuktu is in Mali. Captial is Bamako.

    agent.run(query)
    print("\n[Done]")


if __name__ == "__main__":
    test_reflexion()
