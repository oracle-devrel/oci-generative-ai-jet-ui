_question = ("From your own case decisions in this run: which customers did you escalate, what is the "
             "total exposure now under review, and which single case should a human reviewer pick up "
             "first, and why?")
print("USER:", _question)
print("\nAGENT:", agent_turn(_question, thread_id=TRIAGE_THREAD, max_iterations=6, budget_seconds=120.0))
