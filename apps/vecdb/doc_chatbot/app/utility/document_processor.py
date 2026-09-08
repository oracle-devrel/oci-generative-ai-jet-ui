import PyPDF2
import streamlit as st
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Document Processing Classes
class DocumentProcessor:
    def __init__(self):
        pass

    def extract_pdf_text(self, uploaded_file) -> str:
        try:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
            if not text:
                st.error(
                    "No text could be extracted from the PDF file. Please check the document."
                )
            return text
        except Exception as e:
            st.error(f"Failed to extract text from PDF: {e}")
            return ""

    def extract_txt_text(self, uploaded_file) -> str:
        try:
            return str(uploaded_file.read(), "utf-8")
        except Exception as e:
            st.error(f"Failed to extract text from TXT file: {e}")
            return ""

    def chunk_text(
        self, text: str, chunk_size: int = 500, overlap: int = 50
    ) -> List[str]:
        """
        Chunk text using LangChain's RecursiveCharacterTextSplitter for natural, recursive splitting.
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
        )
        return splitter.split_text(text)
