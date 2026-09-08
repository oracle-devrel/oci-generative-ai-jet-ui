"""Split extracted text into overlapping chunks for embedding."""

from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentChunker:
    """Recursive character text splitter with configurable chunk size and overlap."""

    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk(self, text):
        """Split text into chunks. Returns list of chunk strings."""
        return self.splitter.split_text(text)
