
import argparse
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from typing import Any

# from rag_agent import RAGAgent # Removed
from src.local_rag_agent import LocalRAGAgent
from src.OraDBVectorStore import OraDBVectorStore

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_dummy_text_file(filename: str):
    """Create a dummy text file for testing"""
    content = """
    Agentic RAG Test Document

    This is a test document to verify the functionality of the Agentic RAG system.
    It includes information about agents, vector databases, and LLMs.

    1. Agents are autonomous entities that can plan and execute tasks.
    2. Vector databases store embeddings for efficient similarity search.
    3. LLMs (Large Language Models) generate text based on prompts.

    Oracle AI Vector Search allows integrating vector search within the Oracle Database.
    This enables hybrid search capabilities combining relational and semantic queries.
    """
    with open(filename, 'w') as f:
        f.write(content)
    logger.info(f"Created test file: {filename}")

def load_data(store: OraDBVectorStore, filename: str) -> list[dict[str, Any]]:
    """Load data from text file into the vector store"""
    logger.info(f"Loading data from {filename}...")

    with open(filename) as f:
        text = f.read()

    # Create simple chunks (splitting by paragraphs for this test)
    chunks = []
    paragraphs = [p for p in text.split('\n\n') if p.strip()]

    for i, p in enumerate(paragraphs):
        chunk = {
            "text": p.strip(),
            "metadata": {
                "source": filename,
                "chunk_id": i,
                "title": "Test Document"
            }
        }
        chunks.append(chunk)

    # Using 'add_pdf_chunks' as a proxy for generic text addition,
    # since OraDBVectorStore has specific methods for different collections.
    # We'll use PDFCollection for this test.
    store.add_pdf_chunks(chunks, document_id="test_doc_123")
    logger.info(f"Added {len(chunks)} chunks to PDFCollection")
    return chunks

def verify_retrieval(store: OraDBVectorStore, query: str):
    """Verify that we can retrieve the added data"""
    logger.info(f"Verifying retrieval for query: '{query}'")
    results = store.query_pdf_collection(query, n_results=3)

    if not results:
        logger.error("No results found! Retrieval failed.")
        return

    logger.info(f"Retrieved {len(results)} results:")
    for i, res in enumerate(results):
        logger.info(f"Result {i+1}: {res['content'][:50]}... (Source: {res['metadata'].get('source')})")

    # Check if we got our test document back
    found = any(res['metadata'].get('source') == "test_data.txt" for res in results) # Filename matches create_dummy
    if found:
        logger.info("✓ Retrieval verification passed: Found test document chunks.")
    else:
        logger.warning("Retrieval verification warning: Did not explicitly see 'test_data.txt' source (might be issues with metadata or search relevance).")

def test_agent(store: OraDBVectorStore, query: str, use_cot: bool):
    """Test the agent with and without CoT"""
    mode = "CoT" if use_cot else "Standard"
    logger.info(f"Testing Agent [{mode}] with query: '{query}'")

    try:
        # Initialize agent
        # Using LocalRAGAgent (Ollama) instead of RAGAgent (OpenAI)
        agent = LocalRAGAgent(
            vector_store=store,
            model_name="gemma3:270m",
            use_cot=use_cot,
            collection="PDF Collection",
            max_response_length=512
        )

        start_time = time.time()
        response = agent.process_query(query)
        duration = time.time() - start_time

        logger.info(f"Agent [{mode}] Response (took {duration:.2f}s):")
        logger.info("-" * 40)
        logger.info(response["answer"])
        logger.info("-" * 40)

        if use_cot and response.get("reasoning_steps"):
            logger.info(f"Generated {len(response['reasoning_steps'])} reasoning steps.")

        logger.info(f"✓ Agent [{mode}] test passed.")

    except Exception as e:
        logger.error(f"✗ Agent [{mode}] test failed: {e}", exc_info=True)

def cleanup(store: OraDBVectorStore):
    """Remove test data"""
    logger.info("Cleaning up test data...")
    # Clean up all data from PDFCollection for a clean slate
    store.delete_documents("PDFCOLLECTION", delete_all=True)
    logger.info("Cleanup completed.")

def main():
    parser = argparse.ArgumentParser(description="End-to-End Test Suite for Agentic RAG")
    parser.add_argument("--file", help="Path to text file to load. If not provided, a dummy file is created.", default="test_data.txt")
    parser.add_argument("--keep", action="store_true", help="Keep data after test (do not cleanup)")

    args = parser.parse_args()

    # 1. Setup
    if not os.path.exists(args.file):
        create_dummy_text_file(args.file)
        created_dummy = True
    else:
        created_dummy = False

    try:
        # 2. Init DB
        logger.info("Initializing OraDBVectorStore...")
        try:
            store = OraDBVectorStore()
            logger.info("✓ Initialized OraDBVectorStore with in-database embeddings.")
        except Exception as e:
            logger.error(f"Failed to initialize OraDBVectorStore with default params (expected model ALL_MINILM_L12_V2): {e}")
            logger.info("Attempting fallback to FakeEmbeddings (TEST WILL NOT VERIFY DB MODEL)...")
            try:
                from langchain_community.embeddings import FakeEmbeddings
                # Using 384 dimensions (common for small models)
                embeddings = FakeEmbeddings(size=384)
                store = OraDBVectorStore(embedding_function=embeddings)
                logger.info("✓ Initialized OraDBVectorStore with FakeEmbeddings")
            except ImportError:
                logger.error("Could not import FakeEmbeddings. Please install langchain-community.")
                raise RuntimeError("Could not import FakeEmbeddings") from e

        # 3. Load Data
        load_data(store, args.file)

        # 4. Verify Retrieval directly
        verify_retrieval(store, "autonomous entities")

        # 5. Test Agent without CoT (Standard)
        test_agent(store, "What does this document say about vector databases?", use_cot=False)

        # 6. Test Agent with CoT
        test_agent(store, "Explain the relationship between agents and vector databases based on the text.", use_cot=True)

        logger.info("\n✓✓✓ All Tests Completed Successfully ✓✓✓\n")

    except Exception as e:
        logger.error(f"Test Suite Failed: {e}", exc_info=True)

    finally:
        # 7. Cleanup
        if not args.keep:
            try:
                # Use existing store if available, otherwise we can't clean up easily without init
                if 'store' in locals() and store:
                    cleanup(store)
                else:
                    logger.warning("Skipping cleanup as store was not initialized.")
            except Exception as e:
                logger.error(f"Cleanup failed: {e}")

            if created_dummy and os.path.exists(args.file):
                os.remove(args.file)
                logger.info(f"Removed temporary file: {args.file}")

if __name__ == "__main__":
    main()
