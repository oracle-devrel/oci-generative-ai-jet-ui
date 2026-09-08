"""app.py - Streamlit chat UI for asking questions about Oracle AI Database 26ai.

Built on LangChain Expression Language (LCEL). The retriever pulls from the
DOC_CHUNKS table backed by the OracleVS vector store. Embeddings are
generated INSIDE the database via OracleEmbeddings(provider="database").
The LLM is a local Ollama model.
"""

import os
from operator import itemgetter

import oracledb
import streamlit as st
from dotenv import load_dotenv
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_ollama import OllamaLLM
from langchain_oracledb.embeddings import OracleEmbeddings
from langchain_oracledb.vectorstores.oraclevs import OracleVS

load_dotenv()

ORACLE_USER = os.getenv("ORACLE_USER", "raguser")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "RagUser_2026")
ORACLE_DSN = os.getenv("ORACLE_DSN", "localhost:1521/FREEPDB1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


# ----------------------------------------------------------------------------
# Page setup
# ----------------------------------------------------------------------------

st.set_page_config(
    page_title="Oracle 26ai Docs Assistant",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        /* ======================================================
           Dark theme color system
           Designed for high readability and reduced eye strain.
           Inspired by GitHub Dark, Linear, and Vercel's design.
        ====================================================== */

        :root {
            --bg: #0b0d12;
            --bg-elevated: #12151c;
            --surface: #161922;
            --surface-hover: #1c2029;
            --border: #232833;
            --border-strong: #2d3340;
            --text: #f1f5f9;
            --text-2: #cbd5e1;
            --text-3: #94a3b8;
            --text-muted: #64748b;
            --accent: #6366f1;
            --accent-hover: #7c7ef5;
            --accent-bg: rgba(99, 102, 241, 0.1);
            --accent-border: rgba(99, 102, 241, 0.3);
            --code-bg: #0f1218;
        }

        /* Streamlit overrides */
        html, body, [class*="css"], .stApp {
            background: var(--bg) !important;
            color: var(--text) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        .block-container {
            padding-top: 2.5rem;
            padding-bottom: 4rem;
            max-width: 1200px;
        }

        #MainMenu, footer, header, .stDeployButton {
            visibility: hidden;
            display: none;
        }

        /* ======================================================
           Header
        ====================================================== */
        .app-header {
            margin-bottom: 2.25rem;
            padding-bottom: 1.75rem;
            border-bottom: 1px solid var(--border);
        }

        .app-brand {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin-bottom: 1rem;
        }

        .app-brand-mark {
            width: 30px;
            height: 30px;
            background: linear-gradient(135deg, var(--accent) 0%, #8b5cf6 100%);
            color: white;
            border-radius: 7px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 1rem;
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
        }

        .app-brand-name {
            font-size: 0.92rem;
            font-weight: 600;
            color: var(--text);
            letter-spacing: -0.01em;
        }

        .app-title {
            font-size: 1.7rem;
            font-weight: 700;
            color: var(--text);
            letter-spacing: -0.025em;
            margin: 0 0 0.5rem 0;
            line-height: 1.2;
        }

        .app-subtitle {
            font-size: 0.95rem;
            color: var(--text-3);
            margin: 0;
            line-height: 1.55;
            max-width: 720px;
        }

        /* ======================================================
           Search input
        ====================================================== */
        .stTextInput > div > div > input {
            font-size: 0.98rem;
            font-family: 'Inter', sans-serif;
            padding: 0.9rem 1.15rem;
            border: 1px solid var(--border-strong);
            border-radius: 10px;
            background: var(--surface);
            color: var(--text);
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            transition: all 0.15s ease;
        }

        .stTextInput > div > div > input::placeholder {
            color: var(--text-muted);
        }

        .stTextInput > div > div > input:hover {
            border-color: #3a4150;
            background: var(--surface-hover);
        }

        .stTextInput > div > div > input:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 4px var(--accent-bg);
            background: var(--surface);
        }

        .stTextInput label {
            display: none;
        }

        /* ======================================================
           Suggestion chips
        ====================================================== */
        .suggestions-label {
            font-size: 0.74rem;
            font-weight: 500;
            letter-spacing: 0.04em;
            color: var(--text-muted);
            margin: 1.75rem 0 0.85rem 0;
            text-transform: uppercase;
        }

        .stButton > button {
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--text-2);
            font-family: 'Inter', sans-serif;
            font-size: 0.88rem;
            font-weight: 500;
            padding: 0.7rem 1rem;
            border-radius: 9px;
            transition: all 0.12s ease;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
            width: 100%;
            text-align: left;
            white-space: normal;
            line-height: 1.45;
            min-height: 46px;
        }

        .stButton > button:hover {
            border-color: var(--accent-border);
            color: var(--text);
            background: var(--surface-hover);
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.1);
        }

        .stButton > button:focus,
        .stButton > button:active {
            box-shadow: 0 0 0 3px var(--accent-bg) !important;
            outline: none !important;
            color: var(--text) !important;
            border-color: var(--accent) !important;
            background: var(--surface-hover) !important;
        }

        /* ======================================================
           Section headers
        ====================================================== */
        .section-label {
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin: 0 0 0.85rem 0;
        }

        /* Header row above the answer: section label + reset button.
           Uses Streamlit's st.columns inside answer_col to align them. */
        .answer-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.85rem;
        }

        /* Smaller, subtler button style for the "New question" reset.
           Scoped to a wrapper class so it doesn't affect suggestion chips. */
        .reset-btn .stButton > button {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-3);
            font-size: 0.78rem;
            font-weight: 500;
            padding: 0.3rem 0.75rem;
            border-radius: 6px;
            box-shadow: none;
            min-height: 0;
            width: auto;
        }
        .reset-btn .stButton > button:hover {
            border-color: var(--accent-border);
            color: var(--text);
            background: var(--surface-hover);
            box-shadow: none;
        }

        /* Bottom "try another" row */
        .try-another-section {
            margin-top: 2.5rem;
            padding-top: 1.75rem;
            border-top: 1px solid var(--border);
        }

        /* ======================================================
           Answer panel
        ====================================================== */
        .answer-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem 1.75rem;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            font-size: 0.97rem;
            line-height: 1.7;
            color: var(--text-2);
        }

        .answer-card p {
            margin: 0 0 1rem 0;
        }
        .answer-card p:last-child {
            margin-bottom: 0;
        }

        .answer-card code {
            background: var(--code-bg);
            color: #c4b5fd;
            padding: 0.15rem 0.45rem;
            border-radius: 5px;
            font-size: 0.88em;
            font-family: 'JetBrains Mono', 'SF Mono', Monaco, monospace;
            border: 1px solid var(--border);
        }

        .answer-card pre {
            background: var(--code-bg);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 1.1rem 1.25rem;
            border-radius: 9px;
            overflow-x: auto;
            margin: 1rem 0;
            font-size: 0.85rem;
            line-height: 1.65;
        }

        .answer-card pre code {
            background: transparent;
            color: inherit;
            padding: 0;
            border: none;
            font-size: inherit;
        }

        .answer-card strong {
            color: var(--text);
            font-weight: 600;
        }

        .answer-card a {
            color: var(--accent-hover);
            text-decoration: none;
            border-bottom: 1px solid transparent;
        }
        .answer-card a:hover {
            border-bottom-color: var(--accent-hover);
        }

        /* ======================================================
           Citations panel (right side)
        ====================================================== */
        .citation {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.6rem;
            transition: all 0.12s ease;
        }

        .citation:hover {
            border-color: var(--border-strong);
            background: var(--surface-hover);
        }

        .citation-header {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            margin-bottom: 0.55rem;
        }

        .citation-num {
            flex-shrink: 0;
            width: 22px;
            height: 22px;
            background: var(--accent-bg);
            color: var(--accent-hover);
            border: 1px solid var(--accent-border);
            border-radius: 5px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.72rem;
            font-weight: 600;
        }

        .citation-source {
            color: var(--text);
            font-weight: 600;
            font-size: 0.83rem;
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .citation-page {
            color: var(--text-muted);
            font-size: 0.76rem;
            font-weight: 500;
            font-family: 'JetBrains Mono', monospace;
        }

        .citation-text {
            color: var(--text-3);
            font-size: 0.83rem;
            line-height: 1.55;
        }

        /* ======================================================
           Footer
        ====================================================== */
        .footer-note {
            margin-top: 3rem;
            padding: 1.25rem 1.5rem;
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-3);
            font-size: 0.85rem;
            line-height: 1.65;
            display: flex;
            align-items: flex-start;
            gap: 0.65rem;
        }

        .footer-note-icon {
            flex-shrink: 0;
            color: var(--accent);
            font-size: 1rem;
            margin-top: 0.05rem;
        }

        .footer-note strong {
            color: var(--text);
            font-weight: 600;
        }

        /* ======================================================
           Spinner
        ====================================================== */
        .stSpinner > div > div {
            border-top-color: var(--accent) !important;
        }

        .stSpinner > div {
            color: var(--text-3) !important;
        }

    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# Backend
# ----------------------------------------------------------------------------

def format_docs(docs):
    return "\n\n".join(d.page_content for d in docs)


@st.cache_resource(show_spinner="Connecting to Oracle AI Database 26ai...")
def setup_chain():
    connection = oracledb.connect(
        user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN
    )

    embeddings = OracleEmbeddings(
        conn=connection,
        params={"provider": "database", "model": "ALL_MINILM_L12_V2"},
    )

    vector_store = OracleVS(
        client=connection,
        embedding_function=embeddings,
        table_name="DOC_CHUNKS",
        distance_strategy=DistanceStrategy.COSINE,
    )

    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    llm = OllamaLLM(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert assistant on Oracle AI Database 26ai. "
                "Answer the user's question using ONLY the context below. "
                "Be concise and technical. When code or SQL appears in the "
                "context, include it in your answer using fenced code blocks. "
                "If the answer is not in the context, say so plainly rather "
                "than guessing.\n\n"
                "Context:\n{context}",
            ),
            ("human", "{input}"),
        ]
    )

    answer_step = (
        {
            "context": itemgetter("context") | RunnableLambda(format_docs),
            "input": itemgetter("input"),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return RunnableParallel(
        {
            "input": itemgetter("input"),
            "context": itemgetter("input") | retriever,
        }
    ).assign(answer=answer_step)


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------

# Initialize the LangChain pipeline once per session (cached).
chain = setup_chain()

# Suggested questions, one from each document category plus a cross-doc one.
# Tag is shown as small label above each suggestion; query is what gets sent.
SUGGESTIONS = [
    {
        "tag": "Vector Search",
        "query": "How do I load an ONNX embedding model into Oracle?",
    },
    {
        "tag": "JSON",
        "query": "What is JSON Relational Duality?",
    },
    {
        "tag": "Concepts",
        "query": "How does ACID consistency work in Oracle?",
    },
    {
        "tag": "Cross-document",
        "query": "Can I query JSON columns with vector search?",
    },
]


# Header
st.markdown(
    """
    <div class="app-header">
        <div class="app-brand">
            <div class="app-brand-mark">◆</div>
            <div class="app-brand-name">Oracle 26ai Docs Assistant</div>
        </div>
        <h1 class="app-title">Ask anything about Oracle AI Database 26ai</h1>
        <p class="app-subtitle">
            Retrieval and embeddings run inside the database. Answers come back grounded in source documentation, with citations to the exact pages used.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# Streamlit state pattern that lets suggestion buttons populate the input box.
#
# Streamlit re-runs the script top-to-bottom on every interaction. We can't
# directly write to a widget's session_state key once the widget has rendered.
# So we use a separate "pending_question" key that the suggestion buttons
# write to, and we copy that into the input widget's state BEFORE the widget
# is created on the next run.
# ----------------------------------------------------------------------------

if "pending_question" in st.session_state:
    st.session_state.question_input = st.session_state.pending_question
    del st.session_state.pending_question


def populate_input(query: str):
    """Suggestion-button callback. Sets pending_question; on next rerun,
    that value is moved into question_input before the widget renders."""
    st.session_state.pending_question = query


def reset_question():
    """Clear the input so the user can ask something new.
    Pops question_input from state so the widget is recreated empty
    on the next rerun (Streamlit can't write to a widget's own key
    after the widget exists, so we delete it instead)."""
    if "question_input" in st.session_state:
        del st.session_state.question_input


# Input
question = st.text_input(
    "Question",
    placeholder="What do you want to know?",
    key="question_input",
    label_visibility="collapsed",
)


# Suggestions (empty state)
if not question:
    st.markdown(
        '<div class="suggestions-label">Suggested questions</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, suggestion in enumerate(SUGGESTIONS):
        with cols[i % 2]:
            label = f"{suggestion['tag']}  ›  {suggestion['query']}"
            st.button(
                label,
                key=f"chip_{i}",
                on_click=populate_input,
                args=(suggestion["query"],),
            )


# Results — answer on the left (wider), sources on the right
if question:
    answer_col, sources_col = st.columns([3, 2], gap="large")

    with answer_col:
        # Header row: "Answer" label on the left, "New question" button on the right
        label_col, button_col = st.columns([3, 1])
        with label_col:
            st.markdown(
                '<div class="section-label" style="margin-top: 0.25rem;">Answer</div>',
                unsafe_allow_html=True,
            )
        with button_col:
            st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
            st.button(
                "↺ New question",
                key="reset_btn",
                on_click=reset_question,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        answer_placeholder = st.empty()
        streamed_answer = ""
        retrieved_docs = []

        with st.spinner("Searching the database..."):
            for event in chain.stream({"input": question}):
                if "context" in event:
                    retrieved_docs = event["context"]
                if "answer" in event:
                    streamed_answer += event["answer"]
                    answer_placeholder.markdown(
                        f'<div class="answer-card">{streamed_answer}</div>',
                        unsafe_allow_html=True,
                    )

    with sources_col:
        st.markdown(
            '<div class="section-label">Sources</div>',
            unsafe_allow_html=True,
        )
        for idx, doc in enumerate(retrieved_docs, start=1):
            page = doc.metadata.get("source_page", "?")
            source = doc.metadata.get("source_name", "Unknown")
            preview = doc.page_content[:200].strip().replace("\n", " ")
            if len(doc.page_content) > 200:
                preview += "…"

            st.markdown(
                f"""
                <div class="citation">
                    <div class="citation-header">
                        <div class="citation-num">{idx}</div>
                        <div class="citation-source">{source}</div>
                        <div class="citation-page">p.{page}</div>
                    </div>
                    <div class="citation-text">{preview}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # "Try another" row, full width below the answer/sources columns
    st.markdown('<div class="try-another-section">', unsafe_allow_html=True)
    st.markdown(
        '<div class="suggestions-label">Try another question</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, suggestion in enumerate(SUGGESTIONS):
        with cols[i % 2]:
            label = f"{suggestion['tag']}  ›  {suggestion['query']}"
            st.button(
                label,
                key=f"chip_after_{i}",
                on_click=populate_input,
                args=(suggestion["query"],),
            )
    st.markdown("</div>", unsafe_allow_html=True)


# Footer
st.markdown(
    """
    <div class="footer-note">
        <span class="footer-note-icon">●</span>
        <div>
            <strong>All retrieval runs in-database.</strong>
            Chunking, embedding, and vector search happen inside Oracle AI Database 26ai.
            The local LLM runs on this machine. No external services are contacted.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
