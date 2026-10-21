from workshop.memory import register_user_and_agent

USER_ID  = "enterprise-operator"
AGENT_ID = "enterprise-data-agent"
register_user_and_agent(memory_client,
                        USER_ID, "Operator querying the enterprise database in natural language.",
                        AGENT_ID, "Data agent grounded in scanned schema metadata.")
print(f"OAMP ready ({LLM_PROVIDER} extraction LLM); user and agent registered.")
