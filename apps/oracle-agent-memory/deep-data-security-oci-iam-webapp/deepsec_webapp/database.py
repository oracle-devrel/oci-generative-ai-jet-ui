# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Oracle connection and Agent Memory helpers."""

from typing import Any

import oracledb
from oracleagentmemory.core import OracleDBMemoryStore, SchemaPolicy
from oracleagentmemory.core.deepsec import OracleMemoryEndUserSecurityContext
from oracleagentmemory.core.embedders import Embedder

from deepsec_webapp.config import RuntimeConfig
oracledb.defaults.program = "devrel-developerhub-oracle-agent-memory"


def connection_kwargs(config: RuntimeConfig, user: str, password: str) -> dict[str, Any]:
    """Build python-oracledb connection parameters without empty optional values."""
    kwargs: dict[str, Any] = {
        "user": user,
        "password": password,
        "dsn": config.dsn,
    }
    if config.config_dir is not None:
        kwargs["config_dir"] = config.config_dir
    if config.wallet_location is not None:
        kwargs["wallet_location"] = config.wallet_location
    if config.wallet_password is not None:
        kwargs["wallet_password"] = config.wallet_password
    return kwargs


def create_runtime_pool(config: RuntimeConfig) -> Any:
    """Create the pool as the least-privileged application account."""
    return oracledb.create_pool(
        **connection_kwargs(config, config.app_pool_user, config.app_pool_password),
        min=1,
        max=8,
        increment=1,
    )


def create_embedder(config: RuntimeConfig) -> Embedder:
    """Create the same provider-backed embedder for setup and runtime."""
    kwargs: dict[str, Any] = {
        "model": config.embedding_model,
        "embedding_dimension": config.embedding_dimension,
    }
    if config.embedding_api_key is not None:
        kwargs["api_key"] = config.embedding_api_key
    if config.embedding_api_base is not None:
        kwargs["api_base"] = config.embedding_api_base
    return Embedder(**kwargs)


def create_runtime_store(config: RuntimeConfig, pool: Any) -> OracleDBMemoryStore:
    """Open the existing owner schema through the runtime pool."""
    return OracleDBMemoryStore(
        embedder=create_embedder(config),
        pool=pool,
        schema_policy=SchemaPolicy.NO_CHECK,
        memory_store_id=config.memory_store_id,
        schema_owner=config.owner_user,
    )


# .. start-deepsec-memory-operations
def list_visible_memories(
    config: RuntimeConfig,
    pool: Any,
    user_context: Any,
) -> list[Any]:
    """List rows visible to the effective OCI IAM end user."""
    with OracleMemoryEndUserSecurityContext(user_context):
        store = create_runtime_store(config, pool)
        return store.list("memory", limit=100)


def add_memory(
    config: RuntimeConfig,
    pool: Any,
    user_context: Any,
    content: str,
    target_username: str,
) -> None:
    """Attempt to insert a row for the username supplied by the browser."""
    with OracleMemoryEndUserSecurityContext(user_context):
        store = create_runtime_store(config, pool)
        store.add(
            contents=[content],
            record_type="memory",
            user_ids=[target_username],
        )


# .. end-deepsec-memory-operations
