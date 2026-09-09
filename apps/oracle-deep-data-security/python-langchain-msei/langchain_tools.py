#!/bin/python
#
# $Header: langchain_tools.py 14-may-2026.13:35:04 tanisaga Exp $
#
# langchain_tools.py
#
# Copyright (c) 2026, Oracle and/or its affiliates.
#
#    NAME
#      langchain_tools.py - LangChain tools and prompt definitions for 
#      LangChain Agent Sample HR application
#
#    DESCRIPTION
#      Defines LangChain tools to list tables, inspect schema,
#      and execute SQL query against the HR schema. Also defines the
#      system prompt and helper utilities used by the HR application.
#
#    MODIFIED   (MM/DD/YY)
#    tanisaga    05/14/26 - Creation
#

from langchain_core.tools import tool

# Allowed HR table
HR_TABLE = "HR.EMPLOYEES"


def get_username(conn) -> str:
    """
    Return authenticated end-user identity.
    """

    with conn.cursor() as cursor:

        cursor.execute(
            "select ORA_END_USER_CONTEXT.username "
            "from sys.dual"
        )

        row = cursor.fetchone()

        return row[0] if row else "unknown"


def build_system_prompt(user: str) -> str:
    """
    Build system instructions for the HR assistant.
    """

    return f"""
You are an Oracle HR assistant.

Authenticated user: {user}

Rules:
- Use only SELECT queries.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, MERGE, or TRUNCATE.
- Use only HR schema objects.
- Always inspect table columns before querying.
- Never assume column names.
- If salary or other fields return NULL, 
it may be due to access restrictions.
- If the user says "my", "me", or "I",
  refer to the authenticated user.
- Return responses in plain English.
- Never return JSON.
- Do not expose SQL queries unless requested.
""".strip()


def _format_query_result(cursor, rows) -> str:
    """
    Convert query results into readable text.
    """

    # Extract column names
    headers = [col[0] for col in cursor.description]

    lines = [" | ".join(headers)]

    # Format each row
    for row in rows:

        formatted_row = [
            "NULL" if value is None else str(value)
            for value in row
        ]

        lines.append(" | ".join(formatted_row))

    return "\n".join(lines)


def create_tools(conn):

    @tool
    def list_tables() -> str:
        """
        List available HR tables.
        """

        return f"Tables: {HR_TABLE}"

    @tool
    def describe_table(table_name: str) -> str:
        """
        Return table column names.
        """

        try:
            with conn.cursor() as cursor:

                # Fetch only schema metadata
                cursor.execute(
                    f"SELECT * FROM {table_name} "
                    "WHERE 1=0"
                )

                # Extract column names
                columns = [
                    desc[0]
                    for desc in cursor.description
                ]

                return (
                    f"Table {table_name} columns: "
                    + ", ".join(columns)
                )

        except Exception as exc:

            return (
                f"ERROR fetching schema: {exc}"
            )

    @tool
    def execute_sql(query: str) -> str:
        """
        Execute read-only SQL query.
        """

        clean_query = (
            query.replace("```sql", "")
            .replace("```", "")
            .strip()
            .rstrip(";")
        )

        try:
            with conn.cursor() as cursor:

                cursor.execute(clean_query)

                rows = cursor.fetchall()

                if not rows:
                    return "NO_DATA_FOUND"

                return _format_query_result(
                    cursor,
                    rows,
                )

        except Exception as exc:

            return f"DATABASE_ERROR: {exc}"

    # Register tools
    tools = [
        list_tables,
        describe_table,
        execute_sql,
    ]

    # Tool lookup map
    tool_map = {
        "list_tables":
            list_tables,

        "describe_table":
            describe_table,

        "execute_sql":
            execute_sql,
    }

    return tools, tool_map