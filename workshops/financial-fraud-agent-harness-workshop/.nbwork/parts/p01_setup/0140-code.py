import os
from workshop.llm import configure_llm

LLM_PROVIDER, OCI_ROUTER = configure_llm()
LLM_MODEL = os.environ["LLM_MODEL"]
