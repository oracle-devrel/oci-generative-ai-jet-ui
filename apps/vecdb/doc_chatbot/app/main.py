import logging
import os
import warnings
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

# Import utility functions
from utility.model import ChatModel, EmbeddingGenerator
from utility.document_processor import DocumentProcessor
from oracle_vecdb import OracleVecDB, Configuration

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["TOKENIZERS_PARALLELISM"] = "false"


# Page configuration
st.set_page_config(
    page_title="Doc Chatbot (Oracle VecDB)",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    """Initialize session state variables"""
    if "processed_documents" not in st.session_state:
        st.session_state.processed_documents = []
    if "embeddings" not in st.session_state:
        st.session_state.embeddings = None
    if "chunks" not in st.session_state:
        st.session_state.chunks = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "vdb_connected" not in st.session_state:
        st.session_state.vdb_connected = False
    if "vdb_client" not in st.session_state:
        st.session_state.vdb_client = None
    if "table_name" not in st.session_state:
        st.session_state.table_name = None
    if "vector_table_status" not in st.session_state:
        st.session_state.vector_table_status = False
    # Oracle VecDB connection settings
    if "vecdb_host" not in st.session_state:
        st.session_state.vecdb_host = None
    if "vecdb_username" not in st.session_state:
        st.session_state.vecdb_username = None
    if "vecdb_password" not in st.session_state:
        st.session_state.vecdb_password = None
    if "vecdb_access_token" not in st.session_state:
        st.session_state.vecdb_access_token = None


def sidebar_configuration():
    """Handle sidebar configuration"""
    with st.sidebar:
        st.header("App Configuration ⚙️")

        st.info(
            """Secure Configuration: All settings are stored locally and used only for your chat sessions."""
        )
        st.markdown("---")
        # Vector DB Configuration (Oracle Autonomous Vector Database via ORDS)
        st.subheader("Vector Store (Oracle VecDB)")
        vecdb_host = st.text_input(
            "ORDS VecDB Base URL",
            placeholder="https://<host>/ords/vector3/_/db-api/stable",
            value=st.session_state.vecdb_host or "",
            help="Your Oracle VecDB ORDS endpoint. Example: https://host/ords/vector3/_/db-api/stable/vecdb",
        )
        vecdb_username = st.text_input(
            "Database Username",
            value=st.session_state.vecdb_username or "",
            help="Vector-enabled DB user/schema (e.g., VECTOR3)",
        )
        vecdb_password = st.text_input(
            "Password",
            value=st.session_state.vecdb_password or "",
            type="password",
            help="Password for the DB user",
        )
        vecdb_access_token = st.text_input(
            "Bearer Access Token",
            value=st.session_state.vecdb_access_token or "",
            type="password",
            help="Optional bearer token. When set, username/password are not used.",
        )

        if st.button("Test Connection"):
            if vecdb_host and (
                vecdb_access_token or (vecdb_username and vecdb_password)
            ):
                try:
                    config_kwargs = {"rest_url": vecdb_host.strip()}
                    if vecdb_access_token:
                        config_kwargs["access_token"] = (
                            vecdb_access_token.strip()
                        )
                    else:
                        config_kwargs["username"] = vecdb_username.strip()
                        config_kwargs["password"] = vecdb_password.strip()
                    config = Configuration(**config_kwargs)
                    if (
                        os.getenv("VECDB_SELF_SIGNED_SSL", "false").lower()
                        == "true"
                    ):
                        config.verify_ssl = False
                    vdb_client = OracleVecDB(config)
                    # Lightweight call to validate connectivity/credentials
                    _ = vdb_client.describe_vector_database()
                    st.session_state.vdb_client = vdb_client
                    st.session_state.vdb_connected = True
                    st.success("Successfully connected to Oracle VecDB.")
                except Exception as e:
                    st.session_state.vdb_connected = False
                    st.session_state.vdb_client = None
                    st.error(f"Failed to connect to Oracle VecDB: {e}")
            else:
                st.warning(
                    "Please enter VecDB host and either a bearer token or username/password to connect."
                )

        # Persist config
        st.session_state.vecdb_host = vecdb_host
        st.session_state.vecdb_username = vecdb_username
        st.session_state.vecdb_password = vecdb_password
        st.session_state.vecdb_access_token = vecdb_access_token

        st.markdown("---")
        # LLM Configuration
        st.subheader("Language Model")
        with st.expander("Chat Model Settings", expanded=True):
            chat_model_type = st.selectbox(
                "Model Type",
                ["OpenAI compatible API", "Ollama"],
                help="Choose between an OpenAI-compatible API or a local Ollama model.",
            )
            if chat_model_type == "OpenAI compatible API":
                chat_api_key = st.text_input(
                    "API Key",
                    type="password",
                    help="API key for your LLM provider.",
                )
                chat_base_url = st.text_input(
                    "Base URL",
                    placeholder="https://api.your-provider.com/v1",
                    help="Base URL for your LLM API.",
                )
                chat_model_name = st.text_input(
                    "Model Name",
                    placeholder="your-model-name",
                    help="Name of the LLM model to use.",
                )
                st.info("""
                API Configuration Examples:
                - OpenAI-compatible APIs
                - Base URL examples:
                  - https://api.openai.com/v1 (OpenAI)
                  - https://openrouter.ai/api/v1 (OpenRouter)
                """)
            elif chat_model_type == "Ollama":
                chat_api_key = "dummy"
                chat_base_url = st.text_input(
                    "Base URL",
                    "http://localhost:11434",
                    placeholder="http://localhost:11434",
                    help="Base URL for your local Ollama server.",
                )
                chat_model_name = st.text_input(
                    "Model Name",
                    "llama3",
                    placeholder="llama3",
                    help="Name of the Ollama model to use.",
                )
        st.markdown("---")
        # Embedding Configuration
        st.subheader("Embedding Model")
        with st.expander("Embedding Settings", expanded=True):
            embed_model_type = st.selectbox(
                "Embedding Type",
                ["Sentence-Transformers", "OpenAI compatible API", "Ollama"],
                help="Choose the embedding model type.",
            )
            if embed_model_type == "Sentence-Transformers":
                embed_model_name = st.text_input(
                    "Model Name",
                    "all-MiniLM-L6-v2",
                    placeholder="all-MiniLM-L6-v2",
                    help="Name of the sentence-transformers model.",
                )
                embed_api_key = "dummy"
                embed_base_url = "dummy"
            elif embed_model_type == "OpenAI compatible API":
                embed_base_url = st.text_input(
                    "Embedding Base URL",
                    placeholder="https://api.your-provider.com/v1",
                    help="Base URL for your embedding API.",
                )
                embed_api_key = st.text_input(
                    "Embedding API Key",
                    type="password",
                    help="API key for your embedding provider.",
                )
                embed_model_name = st.text_input(
                    "Embedding Model Name",
                    placeholder="text-embedding-ada-002",
                    help="Name of the embedding model to use.",
                )
                st.info("""
                Embedding API Configuration:
                - OpenAI-compatible APIs
                - Model examples:
                  - text-embedding-ada-002 (OpenAI)
                  - text-embedding-3-small (OpenAI)
                  - openai/text-embedding-ada-002 (OpenRouter)
                """)
            elif embed_model_type == "Ollama":
                embed_base_url = st.text_input(
                    "Ollama base URL",
                    "http://localhost:11434",
                    placeholder="http://localhost:11434",
                    help="Base URL for your local Ollama server.",
                )
                embed_model_name = st.text_input(
                    "Ollama Model Name",
                    "all-minilm:latest",
                    placeholder="all-minilm:latest",
                    help="Name of the Ollama embedding model.",
                )
                embed_api_key = "dummy"

        # Store configuration in session state
        st.session_state.chat_model_type = (
            "API"
            if chat_model_type == "OpenAI compatible API"
            else chat_model_type
        )
        st.session_state.chat_model_name = chat_model_name
        st.session_state.chat_api_key = chat_api_key
        st.session_state.chat_base_url = chat_base_url
        st.session_state.embed_model_type = (
            "API"
            if embed_model_type == "OpenAI compatible API"
            else embed_model_type
        )
        st.session_state.embed_model_name = embed_model_name
        st.session_state.embed_api_key = embed_api_key
        st.session_state.embed_base_url = embed_base_url


def document_process_and_upload_tab():
    """Document upload and processing tab"""
    st.subheader("Document Upload")

    # File upload
    uploaded_files = st.file_uploader(
        "Choose PDF or TXT files",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        help="Upload multiple documents to create your knowledge base",
    )

    if uploaded_files:
        st.info(f"{len(uploaded_files)} file(s) uploaded")

        # Document processing parameters
        st.subheader("Processing Parameters")
        col1, col2 = st.columns(2)

        with col1:
            chunk_size = st.slider(
                "Chunk Size",
                100,
                2000,
                500,
                step=50,
                help="Size of each text chunk in words",
            )

        with col2:
            overlap_size = st.slider(
                "Overlap Size",
                0,
                500,
                50,
                step=10,
                help="Number of overlapping words between chunks",
            )

        st.subheader("Vector table name")
        table_name = st.text_input("Table Name", value="qa_chatbot_docs")
        # Process documents
        if st.button("Process Documents", type="primary"):

            if not st.session_state.get("vdb_connected", False):
                st.warning(
                    "Please connect to Oracle VecDB before processing documents."
                )
                return
            if not st.session_state.vdb_client:
                st.error("VecDB client not initialized.")
                return

            with st.spinner("Processing and generating embeddings..."):
                processor = DocumentProcessor()

                # Get embedding configuration from session state
                embed_model_type = st.session_state.get(
                    "embed_model_type", "local"
                )
                embed_model_name = st.session_state.get(
                    "embed_model_name", "all-MiniLM-L6-v2"
                )
                embed_api_key = st.session_state.get("embed_api_key", "")
                embed_base_url = st.session_state.get("embed_base_url", "")

                embedding_gen = EmbeddingGenerator(
                    embed_model_type,
                    embed_model_name,
                    embed_api_key,
                    embed_base_url,
                )

                if not embedding_gen.status:
                    st.error(
                        "Embedding model configuration is invalid. Please check your settings."
                    )
                    return

                all_chunks = []
                processed_docs = []

                for uploaded_file in uploaded_files:
                    if uploaded_file.type == "application/pdf":
                        text = processor.extract_pdf_text(uploaded_file)
                    else:
                        text = processor.extract_txt_text(uploaded_file)

                    if text:
                        chunks = processor.chunk_text(
                            text, chunk_size, overlap_size
                        )

                        for i, chunk in enumerate(chunks):
                            all_chunks.append(
                                {
                                    "text": chunk,
                                    "source": uploaded_file.name,
                                    "chunk_id": i,
                                    "length": len(chunk),
                                }
                            )

                        processed_docs.append(
                            {
                                "name": uploaded_file.name,
                                "chunks": len(chunks),
                                "total_length": len(text),
                            }
                        )

                if all_chunks:
                    # Generate embeddings
                    embeddings = embedding_gen.generate_embeddings(
                        [chunk["text"] for chunk in all_chunks]
                    )

                    # Store in session state
                    st.session_state.chunks = all_chunks
                    st.session_state.embeddings = embeddings
                    st.session_state.processed_documents = processed_docs

                    st.success(
                        f"Successfully processed {len(processed_docs)} documents into {len(all_chunks)} chunks"
                    )

                    # Show summary
                    df_summary = pd.DataFrame(processed_docs)
                    st.dataframe(df_summary, width="stretch")
                else:
                    st.error(
                        "No text could be extracted from the uploaded documents. Please check your files."
                    )
                    return

            with st.spinner(
                f"Uploading to Oracle VecDB... {len(st.session_state.chunks)} chunks"
            ):
                try:
                    # Recreate table
                    try:
                        st.session_state.vdb_client.drop_vector_table(
                            name=table_name
                        )
                        st.info("Dropped existing vector table (if existed).")
                    except Exception as exc:
                        logging.debug(
                            "Drop vector table %s skipped: %s",
                            table_name,
                            exc,
                        )

                    # Create a dense vector table and index
                    st.session_state.vdb_client.create_vector_table(
                        name=table_name,
                        comment="Doc Chatbot document chunks",
                    )
                    try:
                        st.session_state.vdb_client.create_index(
                            table_name=table_name
                        )
                    except Exception as exc:
                        logging.info(
                            "Index creation skipped for %s: %s",
                            table_name,
                            exc,
                        )

                    # Prepare upsert payload
                    records = []
                    for ix in range(len(st.session_state.embeddings)):
                        records.append(
                            {
                                "id": f"vec_{ix}",
                                "metadata": {
                                    "source": st.session_state.chunks[ix][
                                        "source"
                                    ],
                                    "text": st.session_state.chunks[ix]["text"],
                                    "chunk_id": st.session_state.chunks[ix][
                                        "chunk_id"
                                    ],
                                },
                                "dense_vector": st.session_state.embeddings[
                                    ix
                                ].tolist(),
                            }
                        )

                    st.info("Uploading records to Oracle VecDB...")
                    _ = st.session_state.vdb_client.upsert_vectors(
                        table_name=table_name, vectors=records
                    )
                    st.success(
                        f"Uploaded {len(records)} vectors to the vector table."
                    )

                    st.session_state.table_name = table_name
                    st.session_state.vector_table_status = True
                except Exception as e:
                    st.error(f"Failed to upload vectors to Oracle VecDB: {e}")


def _normalize_query_result(result: Any) -> List[Dict[str, Any]]:
    """
    Normalize VecDB query response into a list of match dicts.
    Handles:
    - Pydantic BaseModel (VecDBSearchItem or collections)
    - dict responses with 'items' or 'matches'
    - single-item responses with id/metadata
    - ignores empty/None-only objects
    """

    def to_plain(obj: Any) -> Any:
        # Prefer Pydantic model_dump with exclude_none to drop None-only fields
        if hasattr(obj, "model_dump"):
            try:
                return obj.model_dump(exclude_none=True)
            except Exception as exc:
                logging.debug("model_dump with exclude_none failed: %s", exc)
                try:
                    return obj.model_dump()
                except Exception as inner_exc:
                    logging.debug("model_dump fallback failed: %s", inner_exc)
        if hasattr(obj, "to_dict"):
            try:
                return obj.to_dict()
            except Exception as exc:
                logging.debug("to_dict failed: %s", exc)
        return obj

    r = to_plain(result)
    # If response is a single BaseModel/dict with only None/empty fields (e.g., id=None, metadata=None, ...), treat as no matches
    if isinstance(r, dict):
        has_non_empty = any(val not in (None, {}, [], "") for val in r.values())
        if not has_non_empty:
            return []

    def is_meaningful_item(item: Any) -> bool:
        # Consider an item meaningful if it has non-empty metadata or at least a 'text' field in metadata
        if isinstance(item, dict):
            md = item.get("metadata")
            if isinstance(md, dict):
                return bool(md) or ("text" in md)
        return False

    matches: List[Dict[str, Any]] = []

    # Case 1: list of items
    if isinstance(r, list):
        for it in r:
            itp = to_plain(it)
            if is_meaningful_item(itp):
                matches.append(itp)
        return matches

    # Case 2: dict with container keys
    if isinstance(r, dict):
        for key in ("items", "matches", "data", "results"):
            if key in r and isinstance(r[key], list):
                for it in r[key]:
                    itp = to_plain(it)
                    if is_meaningful_item(itp):
                        matches.append(itp)
                return matches

        # Single item dict
        if is_meaningful_item(r):
            matches.append(r)
        return matches

    # Case 3: BaseModel-like object not converted to dict (attribute access)
    if hasattr(result, "metadata") or hasattr(result, "id"):
        md = getattr(result, "metadata", None)
        if isinstance(md, dict) and md:
            item: Dict[str, Any] = {"metadata": md}
            _id = getattr(result, "id", None)
            if _id is not None:
                item["id"] = _id
            dist = getattr(result, "distance", None)
            if dist is not None:
                item["distance"] = dist
            matches.append(item)
        return matches

    # Unknown or empty shape -> no matches
    return matches


def chat_interface():
    """Main chat interface"""

    # Chat interface
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Ask Questions About Your Documents")
    with col2:
        top_k = st.slider(
            "Top K", 1, 10, 5, step=1, help="Top K documents for RAG"
        )
    # Add Clear Chat button
    if st.button("🧹 Clear Chat", help="Clear the current chat history."):
        st.session_state.chat_history = []
        try:
            st.rerun()
        except AttributeError:
            st.experimental_rerun()
    # Initialize chat model
    try:
        chat_model = ChatModel(
            st.session_state.chat_model_type,
            st.session_state.chat_model_name,
            st.session_state.chat_api_key,
            st.session_state.chat_base_url,
        )
        if chat_model.status:
            st.success("Chat model initialized.")
        else:
            st.warning(
                "Chat model could not be initialized. Please check your configuration."
            )
    except Exception as e:
        st.error(f"Failed to initialize chat model: {e}")
        return

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            if "context" in message:
                with st.expander("context"):
                    st.text(f'{message["context"]}')
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Add user message to chat history
        st.session_state.chat_history.append(
            {"role": "user", "content": prompt}
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    context = None

                    if st.session_state.vector_table_status:

                        # Get embedding for the question
                        embed_model_type = st.session_state.get(
                            "embed_model_type", "local"
                        )
                        embed_model_name = st.session_state.get(
                            "embed_model_name", "all-MiniLM-L6-v2"
                        )
                        embed_api_key = st.session_state.get(
                            "embed_api_key", ""
                        )
                        embed_base_url = st.session_state.get(
                            "embed_base_url", ""
                        )

                        embedding_gen = EmbeddingGenerator(
                            embed_model_type,
                            embed_model_name,
                            embed_api_key,
                            embed_base_url,
                        )

                        question_embedding = embedding_gen.generate_embeddings(
                            [prompt]
                        )[0]

                        # Query Oracle VecDB directly
                        search_results = st.session_state.vdb_client.query(
                            table_name=st.session_state.table_name,
                            query_by={"vector": question_embedding.tolist()},
                            top_k=int(top_k),
                            include_vectors=False,
                        )

                        matches = _normalize_query_result(search_results)

                        context = ""
                        if not matches:
                            st.info(
                                "No relevant chunks found for this question."
                            )
                        else:
                            for ix, result in enumerate(matches):
                                md = result.get("metadata", {})
                                if isinstance(md, dict) and "text" in md:
                                    context += f"Chunk {ix+1}: {md['text']}\n\n"

                            if context:
                                with st.expander("context"):
                                    st.text(context)

                    # Generate response
                    response = chat_model.generate_response(prompt, context)
                    st.markdown(response)

                    # Add assistant response to chat history
                    if context:
                        st.session_state.chat_history.append(
                            {
                                "role": "assistant",
                                "content": response,
                                "context": context,
                            }
                        )
                    else:
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": response}
                        )

                except Exception as e:
                    st.error(f"Unable to generate a response: {e}")


def main():
    """Main application function"""
    init_session_state()

    # Sidebar configuration
    sidebar_configuration()

    st.header("Doc Chatbot | Oracle Autonomous Vector Database")
    st.markdown("A RAG-based QA chatbot using Oracle VecDB as the vector store")

    # Container with tabs for other functions
    with st.expander("Document Management", expanded=True):
        document_process_and_upload_tab()

    # Main chat interface
    chat_interface()


if __name__ == "__main__":
    main()
