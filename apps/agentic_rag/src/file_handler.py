"""
File handling utilities for document processing.

Supports processing various file types for RAG ingestion or temporary context.
"""

import re
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# File type handlers
SUPPORTED_EXTENSIONS = {
    # Documents
    ".pdf": "pdf",
    ".txt": "text",
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "text",

    # Code files
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".jsx": "code",
    ".tsx": "code",
    ".java": "code",
    ".c": "code",
    ".cpp": "code",
    ".h": "code",
    ".hpp": "code",
    ".go": "code",
    ".rs": "code",
    ".rb": "code",
    ".php": "code",
    ".swift": "code",
    ".kt": "code",
    ".scala": "code",
    ".sql": "code",
    ".sh": "code",
    ".bash": "code",
    ".zsh": "code",
    ".ps1": "code",
    ".yaml": "code",
    ".yml": "code",
    ".json": "code",
    ".xml": "code",
    ".html": "code",
    ".css": "code",
    ".scss": "code",
    ".less": "code",

    # Data files
    ".csv": "text",
    ".tsv": "text",
    ".log": "text",
}

# In-memory storage for temporary context files
# Key: session_id or file_id, Value: file content and metadata
_temporary_files: Dict[str, Dict[str, Any]] = {}


class FileHandler:
    """Handles file processing for RAG and temporary context."""

    def __init__(self, documents_dir: str = "./documents", vector_store=None):
        """
        Initialize the file handler.

        Args:
            documents_dir: Base directory for @file references
            vector_store: Vector store instance for permanent storage
        """
        self.documents_dir = Path(documents_dir)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store = vector_store
        self._pdf_processor = None

    @property
    def pdf_processor(self):
        """Lazy load PDF processor."""
        if self._pdf_processor is None:
            try:
                from .pdf_processor import PDFProcessor
                self._pdf_processor = PDFProcessor()
            except ImportError:
                from pdf_processor import PDFProcessor
                self._pdf_processor = PDFProcessor()
        return self._pdf_processor

    def get_file_type(self, filename: str) -> str:
        """Determine file type from extension."""
        ext = Path(filename).suffix.lower()
        return SUPPORTED_EXTENSIONS.get(ext, "unknown")

    def is_supported(self, filename: str) -> bool:
        """Check if file type is supported."""
        return self.get_file_type(filename) != "unknown"

    def find_file(self, filename: str) -> Optional[Path]:
        """
        Find a file by name in the documents directory.

        Supports:
        - Exact filename: document.pdf
        - Relative path: ./subdir/document.pdf
        - Home path: ~/docs/document.pdf
        - Absolute path: /path/to/document.pdf
        """
        # Handle home directory
        if filename.startswith("~/"):
            path = Path(filename).expanduser()
            if path.exists():
                return path
            return None

        # Handle absolute path
        if filename.startswith("/"):
            path = Path(filename)
            if path.exists():
                return path
            return None

        # Handle relative path from documents dir
        path = self.documents_dir / filename
        if path.exists():
            return path

        # Try current working directory
        cwd_path = Path.cwd() / filename
        if cwd_path.exists():
            return cwd_path

        # Search recursively in documents dir
        for found in self.documents_dir.rglob(filename):
            return found

        return None

    def read_text_file(self, filepath: Path) -> str:
        """Read a text-based file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(filepath, "r", encoding="latin-1") as f:
                return f.read()

    def process_file(self, filepath: Path) -> Dict[str, Any]:
        """
        Process a file and return its content and metadata.

        Returns:
            Dict with keys: content, chunks, metadata, file_type
        """
        file_type = self.get_file_type(filepath.name)
        metadata = {
            "source": str(filepath),
            "filename": filepath.name,
            "file_type": file_type,
            "size_bytes": filepath.stat().st_size,
            "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
        }

        if file_type == "pdf":
            # Use PDF processor
            chunks, doc_id = self.pdf_processor.process_pdf(str(filepath))
            content = "\n\n".join([c["text"] for c in chunks])
            return {
                "content": content,
                "chunks": chunks,
                "metadata": metadata,
                "file_type": file_type,
                "document_id": doc_id,
            }

        elif file_type in ["text", "markdown", "code"]:
            content = self.read_text_file(filepath)
            # Create simple chunks for text files
            chunks = self._chunk_text(content, filepath.name, metadata)
            return {
                "content": content,
                "chunks": chunks,
                "metadata": metadata,
                "file_type": file_type,
                "document_id": str(uuid.uuid4()),
            }

        else:
            raise ValueError(f"Unsupported file type: {filepath.suffix}")

    def _chunk_text(
        self,
        text: str,
        filename: str,
        base_metadata: Dict[str, Any],
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """Split text into chunks for vector storage."""
        chunks = []

        # Simple chunking by character count with overlap
        start = 0
        chunk_idx = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]

            # Try to break at a natural boundary
            if end < len(text):
                # Look for paragraph break
                last_para = chunk_text.rfind("\n\n")
                if last_para > chunk_size // 2:
                    end = start + last_para
                    chunk_text = text[start:end]
                else:
                    # Look for sentence break
                    last_sentence = max(
                        chunk_text.rfind(". "),
                        chunk_text.rfind(".\n"),
                        chunk_text.rfind("? "),
                        chunk_text.rfind("! ")
                    )
                    if last_sentence > chunk_size // 2:
                        end = start + last_sentence + 1
                        chunk_text = text[start:end]

            chunk_metadata = {
                **base_metadata,
                "chunk_id": f"{filename}_{chunk_idx}",
                "chunk_index": chunk_idx,
            }

            chunks.append({
                "text": chunk_text.strip(),
                "metadata": chunk_metadata,
            })

            chunk_idx += 1
            start = end - overlap if end < len(text) else len(text)

        return chunks

    def add_to_rag(
        self,
        filepath: Path,
        collection: str = "GENERALCOLLECTION"
    ) -> Dict[str, Any]:
        """
        Process a file and add it to the RAG vector store.

        Args:
            filepath: Path to the file
            collection: Target collection (PDF, Web, Repository, General)

        Returns:
            Dict with processing results
        """
        if not self.vector_store:
            raise ValueError("Vector store not configured")

        result = self.process_file(filepath)
        chunks = result["chunks"]

        # Map collection names to vector store methods
        collection_map = {
            "PDFCOLLECTION": "add_pdf_chunks",
            "WEBCOLLECTION": "add_web_chunks",
            "REPOCOLLECTION": "add_repo_chunks",
            "GENERALCOLLECTION": "add_general_knowledge",
            # Aliases
            "pdf": "add_pdf_chunks",
            "web": "add_web_chunks",
            "repository": "add_repo_chunks",
            "repo": "add_repo_chunks",
            "general": "add_general_knowledge",
        }

        method_name = collection_map.get(collection, "add_general_knowledge")
        method = getattr(self.vector_store, method_name, None)

        if method:
            method(chunks, result["document_id"])
            result["stored_in"] = collection
            result["chunks_stored"] = len(chunks)
            print(f"✅ [FileHandler] Added {len(chunks)} chunks to {collection}")
        else:
            raise ValueError(f"Unknown collection: {collection}")

        return result

    def add_temporary(
        self,
        filepath: Path,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a file and store it temporarily for context injection.

        Args:
            filepath: Path to the file
            session_id: Optional session ID to associate with

        Returns:
            Dict with file_id and processing results
        """
        result = self.process_file(filepath)
        file_id = str(uuid.uuid4())

        _temporary_files[file_id] = {
            "content": result["content"],
            "metadata": result["metadata"],
            "chunks": result["chunks"],
            "created": datetime.now().isoformat(),
            "session_id": session_id,
        }

        result["file_id"] = file_id
        result["storage_mode"] = "temporary"
        print(f"📎 [FileHandler] Stored temporary file: {filepath.name} ({file_id})")

        return result

    def get_temporary_content(self, file_id: str) -> Optional[str]:
        """Get content from a temporary file."""
        if file_id in _temporary_files:
            return _temporary_files[file_id]["content"]
        return None

    def remove_temporary(self, file_id: str) -> bool:
        """Remove a temporary file from storage."""
        if file_id in _temporary_files:
            del _temporary_files[file_id]
            return True
        return False

    def list_temporary_files(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all temporary files, optionally filtered by session."""
        files = []
        for fid, data in _temporary_files.items():
            if session_id is None or data.get("session_id") == session_id:
                files.append({
                    "file_id": fid,
                    "filename": data["metadata"]["filename"],
                    "created": data["created"],
                    "size_bytes": data["metadata"]["size_bytes"],
                })
        return files

    def list_documents_dir(self) -> List[Dict[str, Any]]:
        """List files in the documents directory."""
        files = []
        for path in self.documents_dir.rglob("*"):
            if path.is_file() and self.is_supported(path.name):
                files.append({
                    "filename": path.name,
                    "path": str(path.relative_to(self.documents_dir)),
                    "file_type": self.get_file_type(path.name),
                    "size_bytes": path.stat().st_size,
                    "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                })
        return files


def parse_file_references(message: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Parse @file and @@file references from a message.

    Patterns:
    - @filename.ext → temporary context
    - @@filename.ext → permanent RAG storage
    - @./path/to/file.ext → relative path
    - @~/path/to/file.ext → home directory path

    Returns:
        Tuple of (cleaned_message, list of file references)
    """
    references = []

    # Pattern for file references
    # @@ for permanent, @ for temporary
    # Supports: filename.ext, ./path/file.ext, ~/path/file.ext, /abs/path/file.ext
    pattern = r'(@@?)((?:\.\/|~\/|\/)?[\w\-\.\/]+\.[\w]+)'

    def replace_ref(match):
        prefix = match.group(1)
        filepath = match.group(2)

        references.append({
            "filepath": filepath,
            "permanent": prefix == "@@",
            "original": match.group(0),
        })

        # Replace with a placeholder that we'll handle later
        return f"[FILE:{filepath}]"

    cleaned = re.sub(pattern, replace_ref, message)

    return cleaned, references
