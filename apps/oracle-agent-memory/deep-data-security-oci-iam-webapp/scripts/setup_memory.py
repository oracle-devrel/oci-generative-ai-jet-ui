# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Create the demo store as its owner and configure its policy as the administrator."""

import oracledb
from oracleagentmemory.core import OracleDBMemoryStore, SchemaPolicy
from oracleagentmemory.core.deepsec import (
    OciGroupPrincipal,
    UserOwnRowsDeepDataSecurityPolicy,
    add_deep_data_security_policies,
    grant_agent_memory_policies,
)

from deepsec_webapp.config import SetupConfig
from deepsec_webapp.database import connection_kwargs, create_embedder
oracledb.defaults.program = "devrel-developerhub-oracle-agent-memory"


def main() -> None:
    """Recreate only this example's managed schema and own-row policy."""
    config = SetupConfig.from_env()
    runtime = config.runtime
    policy = UserOwnRowsDeepDataSecurityPolicy()
    principal = OciGroupPrincipal(config.iam_group)

    admin_connection = oracledb.connect(
        **connection_kwargs(runtime, config.admin_user, config.admin_password)
    )
    owner_connection = oracledb.connect(
        **connection_kwargs(runtime, runtime.owner_user, config.owner_password)
    )
    try:
        OracleDBMemoryStore(
            embedder=create_embedder(runtime),
            pool=owner_connection,
            schema_policy=SchemaPolicy.RECREATE,
            memory_store_id=runtime.memory_store_id,
        )

        add_deep_data_security_policies(
            admin_connection,
            owner_schema=runtime.owner_user,
            memory_store_id=runtime.memory_store_id,
            policies=[policy],
        )
        grant_agent_memory_policies(
            admin_connection,
            owner_schema=runtime.owner_user,
            memory_store_id=runtime.memory_store_id,
            principals=[principal],
            policies=[policy],
        )
    finally:
        owner_connection.close()
        admin_connection.close()

    print("Created the Agent Memory store and granted its own-row policy.")


if __name__ == "__main__":
    main()
