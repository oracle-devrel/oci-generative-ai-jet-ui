#!/bin/python
#
# $Header: db_conn.py 12-jun-2026.06:19:03 tanisaga Exp $
#
# db_conn.py
#
# Copyright (c) 2026, Oracle and/or its affiliates.
#
#    NAME
#      db_conn.py - Database connection utilities
#
#    DESCRIPTION
#      Creates OCI IAM authenticated Oracle Database connections
#      using Deep Data Security end-user identity propagation.
#
#    NOTES
#      Used by the LangChain application to establish secure
#      database connections on behalf of authenticated users.
#
#    MODIFIED   (MM/DD/YY)
#    tanisaga    06/12/26 - Creation
#

import os
import ssl

import oracledb
import oracledb.plugins.end_user_sec_provider \
    as deepsec_provider

from dotenv import load_dotenv
from pathlib import Path


# Load .env file
load_dotenv()

SSL_CONFIG_DIR = os.getenv("SSL_CONFIG_DIR")

DSN = os.getenv("DB_DSN")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_CREDENTIAL = os.getenv("CLIENT_CREDENTIAL")

AUTHORITY = os.getenv("AUTHORITY")
SCOPES = os.getenv("SCOPES")

# Replace with your token path
TOKEN_PATHS = {
    "marvin": "***/tokens/iam_domain_default/MarvinGreenberg_token",
    "emma": "***/tokens/iam_domain_default/EmmaBaker_token",
}

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def get_token(filename: str) -> str:
    return Path(filename).read_text(encoding="utf-8").strip()


def get_deepsec_authenticated_connection(end_user: str):
    if end_user not in TOKEN_PATHS:
        raise ValueError(f"Unsupported end_user: {end_user}")

    end_user_token = get_token(TOKEN_PATHS[end_user])

    # Set the end-user identity before connecting.
    deepsec_provider.set_end_user_identity(end_user_token)

    conn = oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DSN,
        ssl_context=ssl_ctx,
        ssl_server_dn_match=True,
        ssl_server_cert_dn="CN=server",
        config_dir=SSL_CONFIG_DIR,
        extra_auth_params={
            "end_user_sec_params": {
                "spi_type": "oci_tokens",
                "auth_flow": "client_credentials",
                "client_id": CLIENT_ID,
                "client_credential": CLIENT_CREDENTIAL,
                "authority": AUTHORITY,
                "scopes": SCOPES,
            }
        },
    )

    return conn