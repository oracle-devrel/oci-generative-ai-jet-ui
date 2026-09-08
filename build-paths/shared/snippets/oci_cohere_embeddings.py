"""LangChain Embeddings wrapper for OCI Generative AI (Cohere).

Source: ~/git/personal/oci-genai-service/src/oci_genai_service/inference/embeddings.py:1-60

WHY THIS EXISTS
---------------
`langchain-openai` doesn't speak Cohere on OCI directly — and the OpenAI-compat
endpoint only covers chat, not embeddings. This wrapper hits the OCI
`GenerativeAiInferenceClient.embed_text` directly, then exposes a LangChain
`Embeddings` interface so OracleVS / retrievers consume it as if it were any
other embedder.

Notes:
  * Cohere `embed-english-v3.0` returns 1024-dim vectors.
  * Cohere caps at 96 inputs per call — this wrapper batches automatically.
  * Empty strings are filtered (the API rejects them with 400).

USAGE
-----
    embedder = OciCohereEmbeddings(
        model="cohere.embed-english-v3.0",
        compartment_id=os.environ["OCI_COMPARTMENT_ID"],
    )
    v = embedder.embed_query("hello world")  # list[float], length 1024
    vs = OracleVS.from_texts([...], embedding=embedder, ...)
"""

from __future__ import annotations

import os
from functools import lru_cache

from langchain_core.embeddings import Embeddings


@lru_cache(maxsize=1)
def _client():
    import oci
    from oci.generative_ai_inference import GenerativeAiInferenceClient

    try:
        config = oci.config.from_file("~/.oci/config", "DEFAULT")
        return GenerativeAiInferenceClient(config=config)
    except Exception:
        from oci.auth.signers import InstancePrincipalsSecurityTokenSigner
        signer = InstancePrincipalsSecurityTokenSigner()
        return GenerativeAiInferenceClient(config={}, signer=signer)


class OciCohereEmbeddings(Embeddings):
    BATCH = 96  # Cohere/OCI per-call limit

    def __init__(
        self,
        model: str = "cohere.embed-english-v3.0",
        compartment_id: str | None = None,
        truncate: str = "NONE",
    ):
        self.model = model
        self.compartment_id = compartment_id or os.environ["OCI_COMPARTMENT_ID"]
        self.truncate = truncate

    def _embed(self, texts: list[str]) -> list[list[float]]:
        from oci.generative_ai_inference.models import (
            EmbedTextDetails,
            OnDemandServingMode,
        )

        clean = [t for t in texts if t and t.strip()]
        if not clean:
            return []

        client = _client()
        out: list[list[float]] = []
        for i in range(0, len(clean), self.BATCH):
            batch = clean[i : i + self.BATCH]
            resp = client.embed_text(
                EmbedTextDetails(
                    serving_mode=OnDemandServingMode(model_id=self.model),
                    inputs=batch,
                    truncate=self.truncate,
                    compartment_id=self.compartment_id,
                )
            )
            out.extend(resp.data.embeddings)
        return out

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        result = self._embed([text])
        if not result:
            raise ValueError("embed_query received empty text")
        return result[0]
