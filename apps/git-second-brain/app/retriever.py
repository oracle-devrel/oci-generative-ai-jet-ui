"""
LangChain custom retriever backed by Oracle AI Database 26ai Vector Search.

This retriever embeds the user query with sentence-transformers, runs a
VECTOR_DISTANCE query against the FASTAPI_COMMITS table, and returns
LangChain Document objects with commit metadata.
"""

import array
import os

import oracledb
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field, PrivateAttr
from sentence_transformers import SentenceTransformer


class OracleCommitRetriever(BaseRetriever):
    """Retrieve FastAPI commits from Oracle AI Database 26ai via vector similarity.

    Configuration is read from environment variables:
        ORACLE_USER     – database username
        ORACLE_PASSWORD – database password
        ORACLE_DSN      – Oracle connect string (host:port/service)
    """

    db_user: str = Field(default_factory=lambda: os.environ["ORACLE_USER"])
    db_password: str = Field(default_factory=lambda: os.environ["ORACLE_PASSWORD"], repr=False)
    db_dsn: str = Field(default_factory=lambda: os.environ["ORACLE_DSN"])
    embed_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    top_k: int = 8

    _embed_model: SentenceTransformer = PrivateAttr()
    _conn: oracledb.Connection = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._embed_model = SentenceTransformer(self.embed_model_name)
        self._conn = oracledb.connect(
            user=self.db_user,
            password=self.db_password,
            dsn=self.db_dsn,
        )

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        """Embed the query and run vector search in Oracle 26ai."""
        vec = array.array(
            "f",
            self._embed_model.encode(query, normalize_embeddings=True).tolist(),
        )

        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT sha,
                   TO_CHAR(commit_date, 'YYYY-MM-DD'),
                   author,
                   subject,
                   body,
                   files_changed
            FROM FASTAPI_COMMITS
            ORDER BY VECTOR_DISTANCE(embedding, :1, COSINE)
            FETCH FIRST :2 ROWS ONLY
            """,
            [vec, self.top_k],
        )

        docs = []
        for sha, date_str, author, subject, body, files in cur:
            body_text = body.read() if hasattr(body, "read") else (body or "")
            files_text = files.read() if hasattr(files, "read") else (files or "")

            content = (
                f"Commit: {sha[:10]}\n"
                f"Date: {date_str}\n"
                f"Author: {author}\n"
                f"Subject: {subject}\n"
                f"Body: {body_text}\n"
                f"Files changed:\n{files_text[:800]}"
            )

            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "sha": sha,
                        "date": date_str,
                        "author": author,
                        "subject": subject,
                    },
                )
            )

        cur.close()
        return docs

    def close(self):
        """Clean up the database connection."""
        if self._conn:
            self._conn.close()
