import streamlit as st
import numpy as np
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from typing import List, Optional
from ollama import Client as OllamaClient


class EmbeddingGenerator:
    def __init__(
        self,
        model_type: str,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model_type = model_type
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.model: Optional[SentenceTransformer] = None
        self.client: Optional[object] = None
        self.status = False

        if model_type == "Sentence-Transformers":
            self.model = SentenceTransformer(model_name)
            self.status = True
        elif model_type == "API":
            # Initialize OpenAI client for API-based embeddings
            if api_key and base_url:
                self.client = OpenAI(
                    base_url=(base_url or "").strip(),
                    api_key=(api_key or "").strip(),
                )
                self.status = True
        elif model_type == "Ollama":
            self.client = OllamaClient(host=(base_url or "").strip())
            self.status = True
        # For ollama, will use ollama SDK directly

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        if self.model_type == "Sentence-Transformers":
            if not isinstance(self.model, SentenceTransformer):
                raise ValueError("Sentence-Transformers model not initialized")
            return self.model.encode(
                texts, convert_to_numpy=True, show_progress_bar=False
            )
        elif self.model_type == "API":
            if not isinstance(self.client, OpenAI):
                st.error(
                    "OpenAI client not initialized. Please check your API key and base URL."
                )
                return np.array([[0.0] * 384] * len(texts))
            embeddings = []
            for text in texts:
                try:
                    response = self.client.embeddings.create(
                        input=text, model=self.model_name
                    )

                    embeddings.append(response.data[0].embedding)
                except Exception as e:
                    st.error(f"Failed to generate embedding: {e}")
                    embeddings.append([0.0] * 384)  # Default embedding size
            return np.array(embeddings)
        elif self.model_type == "Ollama":
            try:
                embeddings = []

                if not isinstance(self.client, OllamaClient):
                    raise ValueError("Ollama client not initialized")
                # Loop through each text in the list and generate its embedding
                for text in texts:
                    result = self.client.embeddings(
                        model=self.model_name,
                        prompt=text,
                    )

                    embeddings.append(result.embedding)

                # Convert list of embeddings into a numpy array
                return np.array(embeddings)

            except Exception as e:
                st.error(f"Failed to generate embedding with Ollama SDK: {e}")
                return np.array(
                    [[0.0] * 384] * len(texts)
                )  # Return default embeddings in case of error
        else:
            raise ValueError("Invalid model type")


class ChatModel:
    def __init__(
        self,
        model_type: str,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model_type = model_type
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.client: Optional[object] = None
        self.status = False

        if model_type == "API":
            # Use OpenAI client for OpenAI models
            if api_key:
                self.client = OpenAI(api_key=api_key, base_url=base_url)
                self.status = True
        elif model_type == "Ollama":
            self.client = OllamaClient(host=(base_url or ""))
            self.status = True

    def generate_response(
        self, prompt: str, context: Optional[str] = None
    ) -> str:
        if context:
            full_prompt = (
                f"Context\n: {context}\n\nQuestion\n: {prompt}\n\nAnswer:\n"
            )
        else:
            full_prompt = prompt

        try:
            if self.model_type == "API":
                if not isinstance(self.client, OpenAI):
                    st.error(
                        "OpenAI client not initialized. Please check your API key and base URL."
                    )
                    return "Error: Client not initialized."

                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": full_prompt}],
                        }
                    ],
                )
                content = response.choices[0].message.content
                return content if content is not None else ""

            elif self.model_type == "Ollama":
                if not isinstance(self.client, OllamaClient):
                    st.error(
                        "Ollama client not initialized. Please check your base URL."
                    )
                    return "Error: Client not initialized."
                result = self.client.chat(
                    model=self.model_name,
                    messages=[{"role": "user", "content": full_prompt}],
                )

                message = (
                    result.message.content if hasattr(result, "message") else ""
                )
                return message or ""

        except Exception as e:
            st.error(f"Unable to generate a response: {e}")
            return "Sorry, I couldn't generate a response due to an error."
        return ""
