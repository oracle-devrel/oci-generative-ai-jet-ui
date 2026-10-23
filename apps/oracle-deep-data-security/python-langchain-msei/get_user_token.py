#!/bin/python
#
# $Header: get_user_token.py 14-may-2026.13:40:27 tanisaga Exp $
#
# get_user_token.py
#
# Copyright (c) 2026, Oracle and/or its affiliates.
#
#    NAME
#      get_user_token.py - MSEI authentication utilities
#
#    DESCRIPTION
#      Handles MSEI authentication and access token retrieval
#      for end-user identity propagation.
#
#    NOTES
#      Uses MSAL interactive authentication flow.
#
#    MODIFIED   (MM/DD/YY)
#    tanisaga    05/14/26 - Creation
#
import os

import msal
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")

TENANT_ID = os.getenv("AZURE_TENANT_ID")

SCOPES = [os.getenv("AZURE_SCOPES")]


def get_access_token() -> str:
    """
    Authenticate user and return MSEI access token.
    """

    app = msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=(
            "https://login.microsoftonline.com/"
            f"{TENANT_ID}"
        ),
    )

    result = app.acquire_token_interactive(
        scopes=SCOPES,
    )

    if "access_token" not in result:

        raise RuntimeError(
            f"{result.get('error')}: "
            f"{result.get('error_description')}"
        )

    return result["access_token"]