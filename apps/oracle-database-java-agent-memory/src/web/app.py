import logging
import os
import pathlib
import uuid

import requests
import streamlit as st

logger = logging.getLogger("shopassist")

# --- Constants ---
FAVICON = pathlib.Path(__file__).parent / "favicon.ico"
PAGE_TITLE = "ShopAssist"
WELCOME_MESSAGE = (
    "Welcome to **ShopAssist**! I'm your AI customer support assistant. "
    "I can help you with:\n\n"
    "- **View your orders** and check order status\n"
    "- **Initiate returns** (within 30 days of delivery)\n"
    "- **Answer policy questions** (returns, shipping, support)\n"
    "- **Escalate issues** to a human support agent\n\n"
    "How can I help you today?"
)
QUICK_PROMPTS = [
    "Show my orders",
    "What's the status of ORD-1001?",
    "I want to return ORD-1008",
    "What's your return policy?",
]

# --- Page config ---
st.set_page_config(page_title=PAGE_TITLE, page_icon=str(FAVICON))
st.title(PAGE_TITLE)
st.caption("Customer support powered by AI with Oracle Database")

# --- Sidebar ---
st.sidebar.header("Settings")
backend_url = st.sidebar.text_input(
    "Backend URL",
    value=os.getenv("BACKEND_URL", "http://localhost:8080"),
)

# --- Session state init ---
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Sidebar: Conversations ---
st.sidebar.divider()
if st.sidebar.button("+ New Conversation", use_container_width=True):
    st.session_state.conversation_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.rerun()

try:
    conv_resp = requests.get(
        f"{backend_url.rstrip('/')}/api/v1/agent/conversations", timeout=5
    )
    if conv_resp.ok:
        conversations = conv_resp.json()
        for conv in conversations:
            conv_id = conv["conversationId"]
            label = conv.get("summary") or "Untitled"
            is_active = conv_id == st.session_state.conversation_id
            btn_label = f"{'> ' if is_active else ''}{label}"
            if st.sidebar.button(
                btn_label,
                key=conv_id,
                help=conv_id,
                use_container_width=True,
                disabled=is_active,
            ):
                msg_resp = requests.get(
                    f"{backend_url.rstrip('/')}/api/v1/agent/conversations/{conv_id}/messages",
                    timeout=10,
                )
                if msg_resp.ok:
                    st.session_state.conversation_id = conv_id
                    st.session_state.messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in msg_resp.json()
                    ]
                    st.rerun()
except Exception:
    pass  # Sidebar degrades gracefully if backend is down

st.sidebar.divider()
st.sidebar.caption(f"Active: `{st.session_state.conversation_id[:8]}…`")

# --- Welcome message ---
if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": WELCOME_MESSAGE})


# --- Helper ---
def send_message(prompt, url):
    """Send a prompt to the backend and append both messages to history."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{url.rstrip('/')}/api/v1/agent/chat",
                    data=prompt,
                    headers={
                        "Content-Type": "text/plain",
                        "X-Conversation-Id": st.session_state.conversation_id,
                    },
                    timeout=120,
                )
                resp.raise_for_status()
                answer = resp.text
            except Exception:
                logger.exception("Error contacting backend at %s", url)
                answer = "Sorry, I couldn't reach the assistant right now. Please try again in a moment."
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})


# --- Render history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Quick-start buttons (only on fresh conversation with just the welcome) ---
if len(st.session_state.messages) == 1:
    cols = st.columns(len(QUICK_PROMPTS))
    for col, qp in zip(cols, QUICK_PROMPTS):
        if col.button(qp, use_container_width=True):
            st.session_state.pending_prompt = qp
            st.rerun()

# --- Handle pending prompt from button click ---
if "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")
    send_message(prompt, backend_url)

# --- Handle chat input ---
if prompt := st.chat_input("Type a message..."):
    send_message(prompt, backend_url)
