"""
Git Second Brain - Streamlit Chat UI
Ask natural-language questions about FastAPI's commit history,
powered by Oracle AI Database 26ai Vector Search + LangChain + OpenAI.

Run:
  streamlit run app.py
"""

import os

import streamlit as st
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from retriever import OracleCommitRetriever

# ========================= Page config =========================
st.set_page_config(
    page_title="Git Second Brain",
    page_icon="🧠",
    layout="wide",
)

# ========================= Sidebar =============================
with st.sidebar:
    st.title("Git Second Brain")
    st.caption("Oracle AI Database 26ai + LangChain + OpenAI")

    openai_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Stored only in this session, never persisted.",
    )

    model_name = st.selectbox(
        "Model",
        ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1-nano"],
        index=0,
    )

    top_k = st.slider("Commits to retrieve", min_value=3, max_value=15, value=8)

    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.2, step=0.05)

    st.divider()
    st.markdown(
        "**How it works**\n\n"
        "1. Your question is embedded with sentence-transformers\n"
        "2. Oracle 26ai runs `VECTOR_DISTANCE` to find the most relevant commits\n"
        "3. LangChain passes those commits as context to OpenAI\n"
        "4. You get a grounded answer with commit citations"
    )

    st.divider()
    st.markdown("**Sample questions**")
    sample_questions = [
        "Why did FastAPI switch to Pydantic v2?",
        "How has dependency injection evolved?",
        "What were the biggest breaking changes in the last 2 years?",
        "When did lifespan replace startup/shutdown events?",
        "What security fixes were applied recently?",
    ]
    for q in sample_questions:
        if st.button(q, use_container_width=True):
            st.session_state["prefill"] = q

# ========================= System prompt =======================
SYSTEM_PROMPT = """\
You are Git Second Brain, an AI assistant that answers questions about the
FastAPI open-source project by analyzing its Git commit history.

You will receive a set of relevant commits retrieved from Oracle AI Database 26ai
via vector similarity search. Use ONLY these commits to answer the question.
If the commits do not contain enough information, say so honestly.

Rules:
- Cite specific commits by their short SHA and date when supporting a claim.
- Summarize the narrative arc when multiple commits tell a story.
- Keep answers concise but thorough (3-6 paragraphs max).
- If you are unsure, say "Based on the commits I found..." to hedge.
- Never invent commit SHAs or dates.
"""

RAG_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Retrieved commits:\n\n{context}\n\n---\nQuestion: {question}"),
    ]
)

# ========================= Init state ==========================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "retriever" not in st.session_state:
    with st.spinner("Connecting to Oracle AI Database 26ai ..."):
        st.session_state.retriever = OracleCommitRetriever(top_k=top_k)

# ========================= Chat display ========================
st.header("Ask your repo anything")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"Retrieved commits ({len(msg['sources'])})"):
                for doc in msg["sources"]:
                    meta = doc.metadata
                    st.markdown(
                        f"**`{meta['sha'][:10]}`** | {meta['date']} | "
                        f"*{meta['author']}*\n\n"
                        f"> {meta['subject']}"
                    )
                    st.divider()

# ========================= Chat input ==========================
prefill = st.session_state.pop("prefill", None)
user_input = st.chat_input("Ask about FastAPI's history ...") or prefill

if user_input:
    if not openai_key:
        st.error("Please enter your OpenAI API key in the sidebar.")
        st.stop()

    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Retrieve from Oracle 26ai
    with st.chat_message("assistant"):
        with st.spinner("Searching Oracle 26ai Vector Search ..."):
            retriever = st.session_state.retriever
            retriever.top_k = top_k
            docs = retriever.invoke(user_input)

        context = "\n\n---\n\n".join(doc.page_content for doc in docs)

        # LangChain RAG chain
        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=openai_key,
        )
        chain = RAG_TEMPLATE | llm | StrOutputParser()

        with st.spinner("Generating answer ..."):
            answer = chain.invoke({"context": context, "question": user_input})

        st.markdown(answer)

        # Show retrieved commits
        with st.expander(f"Retrieved commits ({len(docs)})"):
            for doc in docs:
                meta = doc.metadata
                st.markdown(
                    f"**`{meta['sha'][:10]}`** | {meta['date']} | "
                    f"*{meta['author']}*\n\n"
                    f"> {meta['subject']}"
                )
                st.divider()

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "sources": docs,
            }
        )
