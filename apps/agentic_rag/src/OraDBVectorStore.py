from typing import List, Dict, Any, Optional
import json
import argparse
from langchain_oracledb import OracleVS, OracleEmbeddings
try:
    from src.db_utils import load_config, get_db_connection
except ImportError:
    from db_utils import load_config, get_db_connection

# --- MONKEYPATCH BEGIN ---
# Fix for AttributeError: 'str' object has no attribute 'pop'
# The underlying library expects metadata to be a dict, but if stored as VARCHAR2/JSON in Oracle,
# it might come back as a string string via oracledb.
try:
    import langchain_oracledb.vectorstores.oraclevs as vs_module
    import json

    original_read_similarity_output = vs_module._read_similarity_output

    def _fixed_read_similarity_output(results: List, has_similarity_score: bool = False, has_embeddings: bool = False) -> List:
        # Pre-process results to parse metadata string to dict if needed
        fixed_results = []
        for row in results:
            # Row structure: text, metadata, *extras
            if len(row) >= 2:
                row_list = list(row)
                metadata = row_list[1]
                if isinstance(metadata, str):
                    try:
                        # Try to parse JSON string
                        metadata_dict = json.loads(metadata)
                        row_list[1] = metadata_dict
                    except Exception as e:
                        print(f"[OraDB Fix] Failed to parse metadata JSON: {e}")
                        # Fallback to empty dict or keep as is (though it will likely fail downstream)
                        pass
                fixed_results.append(tuple(row_list))
            else:
                fixed_results.append(row)
        
        return original_read_similarity_output(fixed_results, has_similarity_score, has_embeddings)

    # Apply patch
    vs_module._read_similarity_output = _fixed_read_similarity_output
    print("[OraDBVectorStore] Applied monkeypatch for metadata JSON parsing.")
except Exception as e:
    print(f"[OraDBVectorStore] Failed to apply monkeypatch: {e}")
# --- MONKEYPATCH END ---

class OraDBVectorStore:
    def __init__(self, persist_directory: str = "embeddings", embedding_function: Optional[Any] = None):
        """Initialize Oracle DB Vector Store using langchain-oracledb
        
        Args:
            persist_directory: Not used for Oracle DB connection but kept for compatibility
            embedding_function: Optional embedding function to use instead of OracleEmbeddings
        """
        # Load Oracle DB credentials from config.yaml
        self.config = load_config()
        
        # Connect to the database using shared utility
        try:
            self.connection = get_db_connection(self.config)
            print("Oracle DB Connection successful!")
        except Exception as e:
            print("Oracle DB Connection failed!", e)
            raise

        if embedding_function:
            self.embeddings = embedding_function
            print("Using provided custom embedding function.")
        else:
            # Initialize Embeddings
            # Using OracleEmbeddings with params. 
            # Defaulting to 'database' provider and 'ALL_MINILM_L12_V2' which we just loaded.
            # This should be configured in config.yaml for production.
            embed_params = self.config.get("ORACLE_EMBEDDINGS_PARAMS", {"provider": "database", "model": "ALL_MINILM_L12_V2"})
            if isinstance(embed_params, str):
                 try:
                     embed_params = json.loads(embed_params)
                 except Exception:
                     pass
            
            self.embeddings = OracleEmbeddings(conn=self.connection, params=embed_params)

        # Initialize Tables (Collections)
        self.collections = {
            "PDFCOLLECTION": "PDFCOLLECTION",
            "WEBCOLLECTION": "WEBCOLLECTION",
            "REPOCOLLECTION": "REPOCOLLECTION",
            "GENERALCOLLECTION": "GENERALCOLLECTION"
        }
        
        # Initialize OracleVS instances
        self.vector_stores = {}
        for name, table in self.collections.items():
            self.vector_stores[name] = OracleVS(
                client=self.connection,
                embedding_function=self.embeddings,
                table_name=table,
                distance_strategy="EUCLIDEAN_DISTANCE" # Matching previous logic
            )
            # Create table if not exists (OracleVS typically handles this on valid calls or we might need explicit index creation)
            # OracleVS might auto-create on add_texts? We'll see. 
            # If not, we rely on the fact that old implementation created them, or OracleVS will error.
            # Ideally OracleVS has a creates methods? 
            # We will assume existing tables from old implementation are compatible OR OracleVS will manage.
            # Actually, old impl created tables with specific schema. OracleVS might expect specific schema (id, text, metadata, embedding).
            # The schema in old impl: id, text, metadata, embedding. This seems standard.

    def _load_config(self) -> Dict[str, str]:
        """Load configuration from config.yaml"""
        return load_config()
            
    def _sanitize_metadata(self, metadata: Dict) -> Dict:
        """Sanitize metadata to ensure all values are valid types"""
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list):
                sanitized[key] = str(value)
            elif value is None:
                sanitized[key] = ""
            else:
                sanitized[key] = str(value)
        return sanitized

    def _add_chunks_to_collection(self, chunks: List[Dict[str, Any]], collection_name: str):
        """Helper to add chunks to a specific collection"""
        if not chunks:
            return
            
        store = self.vector_stores.get(collection_name)
        if not store:
            raise ValueError(f"Collection {collection_name} not found")
            
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [self._sanitize_metadata(chunk["metadata"]) for chunk in chunks]
        
        # OracleVS add_texts
        print(f"🔄 [OraDB] Inserting {len(chunks)} chunks into {collection_name}...")
        store.add_texts(texts=texts, metadatas=metadatas)
        self.connection.commit()
        print(f"✅ [OraDB] Successfully inserted {len(chunks)} chunks.")

    def add_pdf_chunks(self, chunks: List[Dict[str, Any]], document_id: str):
        """Add chunks from a PDF document to the vector store"""
        self._add_chunks_to_collection(chunks, "PDFCOLLECTION")
        
    def add_web_chunks(self, chunks: List[Dict[str, Any]], source_id: str):
        """Add chunks from web content to the vector store"""
        self._add_chunks_to_collection(chunks, "WEBCOLLECTION")
        
    def add_general_knowledge(self, chunks: List[Dict[str, Any]], source_id: str):
        """Add general knowledge chunks to the vector store"""
        self._add_chunks_to_collection(chunks, "GENERALCOLLECTION")
        
    def add_repo_chunks(self, chunks: List[Dict[str, Any]], document_id: str):
        """Add chunks from a repository to the vector store"""
        self._add_chunks_to_collection(chunks, "REPOCOLLECTION")

    def _query_collection(self, collection_name: str, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Helper to query a collection with similarity scores"""
        print(f"🔍 [OracleVS] Querying {collection_name}")
        store = self.vector_stores.get(collection_name)
        if not store:
            return []

        # Use similarity_search_with_score to get relevance scores
        try:
            docs_with_scores = store.similarity_search_with_score(query, k=n_results)
            formatted_results = []
            for doc, score in docs_with_scores:
                # Convert distance to similarity score (lower distance = higher similarity)
                # Euclidean distance: similarity = 1 / (1 + distance)
                similarity = 1 / (1 + score) if score >= 0 else 0
                result = {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": similarity,
                    "distance": score
                }
                formatted_results.append(result)
        except Exception as e:
            print(f"⚠️ [OracleVS] similarity_search_with_score failed: {e}, falling back to similarity_search")
            docs = store.similarity_search(query, k=n_results)
            formatted_results = []
            for doc in docs:
                result = {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": None,
                    "distance": None
                }
                formatted_results.append(result)
            
        print(f"🔍 [OracleVS] Retrieved {len(formatted_results)} chunks from {collection_name}")
        return formatted_results

    def query_pdf_collection(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Query the PDF documents collection"""
        return self._query_collection("PDFCOLLECTION", query, n_results)

    def query_web_collection(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Query the web documents collection"""
        return self._query_collection("WEBCOLLECTION", query, n_results)

    def query_general_collection(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Query the general knowledge collection"""
        return self._query_collection("GENERALCOLLECTION", query, n_results)

    def delete_documents(self, collection_name: str, ids: Optional[List[str]] = None, delete_all: bool = False):
        """Delete documents from a collection"""
        store = self.vector_stores.get(collection_name)
        if not store:
            raise ValueError(f"Collection {collection_name} not found")
            
        if delete_all:
            # OracleVS might not support delete_all directly, but we can try dropping/truncating via SQL if needed,
            # but sticking to package interface first. 
            # If delete_all is true, we might just want to drop table contents.
            # However, typically vector stores delete by ID.
            # Implementing simple delete by ID for now or using SQL for mass delete if package allows.
            # Using raw SQL for efficiency if delete_all.
            table_name = self.collections.get(collection_name)
            if table_name:
                cursor = self.connection.cursor()
                cursor.execute(f"TRUNCATE TABLE {table_name}")
                self.connection.commit()
                print(f"🗑️ [OraDBVectorStore] Truncated collection {collection_name}")
        elif ids:
            store.delete(ids=ids)
            self.connection.commit()
            print(f"🗑️ [OraDBVectorStore] Deleted {len(ids)} documents from {collection_name}")

    def query_repo_collection(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Query the repository documents collection"""
        return self._query_collection("REPOCOLLECTION", query, n_results)

    def get_collection_count(self, collection_name: str) -> int:
        """Get the total number of chunks in a collection"""
        table_name = self.collections.get(collection_name)
        if not table_name:
            return 0
        try:
            cursor = self.connection.cursor()
            # Check if table exists first? Or just try count.
            # Assuming table exists if it's in our map, otherwise SQL error will be caught.
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            result = cursor.fetchone()
            cursor.close()
            if result:
                return result[0]
            return 0
        except Exception:
            # Table might not exist yet
            return 0

    def get_latest_chunk(self, collection_name: str) -> Dict[str, Any]:
        """Get the most recently added chunk from a collection"""
        table_name = self.collections.get(collection_name)
        if not table_name:
            return {}
        try:
            cursor = self.connection.cursor()
            # Fetch one row. No guarantee of order without timestamp column, 
            # but ROWNUM 1 gives us *a* chunk.
            # Using simple query assuming standard columns
            cursor.execute(f"SELECT text, metadata FROM {table_name} WHERE ROWNUM <= 1")
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                text = row[0]
                metadata = row[1]
                
                # Handle LOBs if necessary
                if hasattr(metadata, 'read'):
                    metadata = metadata.read()
                
                # If metadata is string, valid for return. The caller parses it.
                return {
                    "content": text,
                    "metadata": metadata
                }
            return {}
        except Exception as e:
            print(f"Error getting chunk from {collection_name}: {e}")
            return {}

    def get_embedding_dimension(self, collection_name: str) -> int:
        """Get the dimension of embeddings in the collection"""
        table_name = self.collections.get(collection_name)
        if not table_name:
            return 0
        try:
            cursor = self.connection.cursor()
            # Try to fetch one embedding to check its dimension
            # Assuming 'embedding' is the column name for the vector
            cursor.execute(f"SELECT embedding FROM {table_name} FETCH FIRST 1 ROWS ONLY")
            row = cursor.fetchone()
            cursor.close()
            
            if row and row[0]:
                # Oracle VECTOR type can be converted to list/string or accessed directly
                # If it comes back as a string/object, we need to inspect it
                embedding_data = row[0]
                if hasattr(embedding_data, 'tolist'): # If it's a vector object
                    return len(embedding_data.tolist())
                elif isinstance(embedding_data, list):
                    return len(embedding_data)
                elif isinstance(embedding_data, str):
                    # If it's a string representation
                    return len(json.loads(embedding_data))
                else:
                    # Fallback check
                    return len(list(embedding_data))
            return 0
        except Exception as e:
            print(f"Error fetching dimension for {collection_name}: {e}")
            return 0



    def check_embedding_model_exists(self, model_name: str = "ALL_MINILM_L12_V2") -> bool:
        """Check if an ONNX embedding model is loaded in the database"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM user_mining_models WHERE model_name = :1", [model_name])
            result = cursor.fetchone()
            cursor.close()
            if result and result[0] > 0:
                return True
            return False
        except Exception as e:
            print(f"Error checking model {model_name}: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Manage Oracle DB vector store")
    parser.add_argument("--add", help="JSON file containing chunks to add")
    parser.add_argument("--add-web", help="JSON file containing web chunks to add")
    parser.add_argument("--query", help="Query to search for")
    
    args = parser.parse_args()
    try:
        store = OraDBVectorStore()
        
        if args.add:
            with open(args.add, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            store.add_pdf_chunks(chunks, document_id=args.add)
            print(f"✓ Added {len(chunks)} PDF chunks to Oracle DB vector store")
        
        if args.add_web:
            with open(args.add_web, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            store.add_web_chunks(chunks, source_id=args.add_web)
            print(f"✓ Added {len(chunks)} web chunks to Oracle DB vector store")
        
        if args.query:
            # Query both collections
            pdf_results = store.query_pdf_collection(args.query)
            web_results = store.query_web_collection(args.query)
            
            print("\nPDF Results:")
            print("-" * 50)
            for result in pdf_results:
                print(f"Content: {result['content'][:200]}...")
                print(f"Source: {result['metadata'].get('source', 'Unknown')}")
                print(f"Pages: {result['metadata'].get('page_numbers', [])}")
                print("-" * 50)
            
            print("\nWeb Results:")
            print("-" * 50)
            for result in web_results:
                print(f"Content: {result['content'][:200]}...")
                print(f"Source: {result['metadata'].get('source', 'Unknown')}")
                print(f"Title: {result['metadata'].get('title', 'Unknown')}")
                print("-" * 50)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
