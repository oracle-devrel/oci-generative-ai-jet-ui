from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    oracle_dsn: str = Field(alias="ORACLE_DSN")
    oracle_user: str = Field(alias="ORACLE_USER")
    oracle_password: str = Field(alias="ORACLE_PASSWORD")
    oracle_wallet_location: Path | None = Field(default=None, alias="ORACLE_WALLET_LOCATION")
    oracle_wallet_password: str | None = Field(default=None, alias="ORACLE_WALLET_PASSWORD")
    oracle_vector_enabled: bool = Field(default=False, alias="ORACLE_VECTOR_ENABLED")
    oracle_embedding_model: str = Field(
        default="cohere.embed-english-light-v3.0",
        alias="ORACLE_EMBEDDING_MODEL",
    )
    oracle_vector_table: str = Field(default="LIMITLESS_RESEARCH_VS", alias="ORACLE_VECTOR_TABLE")
    oracle_vector_index_name: str = Field(default="LIMITLESS_RESEARCH_HNSW_IDX", alias="ORACLE_VECTOR_INDEX_NAME")
    oci_region: str | None = Field(default=None, alias="OCI_REGION")
    oci_compartment_id: str | None = Field(default=None, alias="OCI_COMPARTMENT_ID")
    oci_config_file: str = Field(default="~/.oci/config", alias="OCI_CONFIG_FILE")
    oci_auth_profile: str = Field(default="DEFAULT", alias="OCI_AUTH_PROFILE")
    oci_auth_type: str = Field(default="API_KEY", alias="OCI_AUTH_TYPE")
    oci_genai_endpoint: str | None = Field(default=None, alias="OCI_GENAI_ENDPOINT")
    obsidian_vault_path: Path = Field(alias="OBSIDIAN_VAULT_PATH")

    @property
    def uses_wallet(self) -> bool:
        return self.oracle_wallet_location is not None and str(self.oracle_wallet_location).strip() != ""
