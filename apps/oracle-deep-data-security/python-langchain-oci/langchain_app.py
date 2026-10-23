#!/bin/python
#
# $Header: langchain_app.py 12-jun-2026.06:19:03 tanisaga Exp $
#
# langchain_app.py
#
# Copyright (c) 2026, Oracle and/or its affiliates.
#
#    NAME
#      langchain_app.py - OCI IAM LangChain demo entry point
#
#    DESCRIPTION
#      Implements a conversational HR assistant using
#      LangChain, OCI Generative AI, OCI IAM OAuth2
#      authentication, and Oracle Database tools.
#
#    NOTES
#      <other useful comments, qualifications, etc.>
#
#    MODIFIED   (MM/DD/YY)
#    tanisaga    06/12/26 - Creation
#

import logging
import sys

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from langchain_oci import ChatOCIGenAI

from app_config import AppConfig, MODEL_IDS
from db_conn import get_deepsec_authenticated_connection
from langchain_tools import (
    build_system_prompt,
    create_tools,
    get_username,
)

# Maximum tool iterations allowed per request
MAX_TOOL_STEPS = 6

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def main():

    # Load application configuration
    cfg = AppConfig()

    if len(sys.argv) != 2:
        print(
            "Usage: python langchain_app.py <end_user>"
        )
        sys.exit(1)

    end_user = sys.argv[1].lower()

    # Create database connection
    conn = get_deepsec_authenticated_connection(end_user)

    try:
        # Get authenticated end-user identity
        end_user_name = get_username(conn)

        # Build LLM system instructions
        system_prompt = build_system_prompt(end_user_name)

        # Register LangChain tools
        tools, tool_map = create_tools(conn)

        # Initialize OCI Generative AI model
        llm = ChatOCIGenAI(
            model_id=MODEL_IDS[cfg.model_choice],
            compartment_id=cfg.compartment_id,
            service_endpoint=(
                "https://inference.generativeai."
                "us-chicago-1.oci.oraclecloud.com"
            ),
            auth_type="API_KEY",
            auth_profile=cfg.oci_profile,
            auth_file_location=cfg.oci_config_file,
            model_kwargs={
                "temperature": 0,
            },
        )

        # Bind tools to the model
        llm_with_tools = llm.bind_tools(tools)

        print("\nOracle HR Agent Ready")
        print("Type 'exit' to quit")

        while True:

            # Read user input
            user_input = input("\n> ").strip()

            # Exit application
            if user_input.lower() in {"exit", "quit"}:
                break

            # Initialize conversation
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input),
            ]

            # Allow model to iteratively call tools
            for _ in range(MAX_TOOL_STEPS):

                ai_msg = llm_with_tools.invoke(messages)

                messages.append(ai_msg)

                tool_calls = list(
                    getattr(ai_msg, "tool_calls", []) or []
                )

                # Final natural language response
                if not tool_calls:
                    print(f"\n{ai_msg.content.strip()}")
                    break

                # Process first tool call
                tool_call = tool_calls[0]

                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call["id"]

                logger.info(
                    "Tool invoked | name=%s | args=%s",
                    tool_name,
                    tool_args,
                )

                try:
                    # Execute tool
                    tool_result = tool_map[
                        tool_name
                    ].invoke(tool_args)

                    logger.info(
                        "Tool result | name=%s | preview=%s",
                        tool_name,
                        str(tool_result)[:500],
                    )

                except Exception as exc:

                    logger.exception(
                        "Tool execution failed | name=%s",
                        tool_name,
                    )

                    tool_result = (
                        f"TOOL_ERROR: {exc}"
                    )

                # Add tool response back to conversation
                messages.append(
                    ToolMessage(
                        content=tool_result,
                        tool_call_id=tool_call_id,
                    )
                )

            else:
                print("\nMaximum tool steps reached")

    finally:
        # Always close DB connection
        conn.close()


if __name__ == "__main__":
    main()