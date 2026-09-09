#!/bin/python
#
# $Header: db_connection.py 14-may-2026.13:37:28 tanisaga Exp $
#
# db_connection.py
#
# Copyright (c) 2026, Oracle and/or its affiliates.
#
#    NAME
#      db_conn.py - Database connection and security context setup
#
#    DESCRIPTION
#      Creates Oracle database connections and propagates authenticated
#      end-user identity into the database session.
#
#    NOTES
#      Uses Azure AD access tokens for end-user identity propagation.
#
#    MODIFIED   (MM/DD/YY)
#    tanisaga    05/14/26 - Creation
#
import os
import ssl

import oracledb
import oracledb.plugins.end_user_sec_provider \
    as deepsec_provider

from dotenv import load_dotenv

from get_user_token import get_access_token

load_dotenv()

SSL_CONFIG_DIR = os.getenv("SSL_CONFIG_DIR")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN")

CLIENT_ID = os.getenv("DB_CLIENT_ID")

CLIENT_CREDENTIAL = os.getenv(
    "DB_CLIENT_CREDENTIAL"
)

AUTHORITY = os.getenv("DB_AUTHORITY")

SCOPES = os.getenv("DB_SCOPES")

ssl_ctx = ssl.create_default_context()

ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def get_connection():
    """
    Create Oracle database connection with
    end-user identity propagation.
    """

    end_user_token = get_access_token()

    deepsec_provider.set_end_user_identity(
        end_user_token
    )

    return oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        ssl_context=ssl_ctx,
        ssl_server_dn_match=True,
        ssl_server_cert_dn="CN=server",
        config_dir=SSL_CONFIG_DIR,
        extra_auth_params={
            "end_user_sec_params": {
                "spi_type": "azure_tokens",
                "auth_flow": "on_behalf_of",
                "client_id": CLIENT_ID,
                "client_credential":
                    CLIENT_CREDENTIAL,
                "authority": AUTHORITY,
                "scopes": SCOPES,
            }
        },
    )