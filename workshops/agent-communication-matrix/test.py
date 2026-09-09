from mcp.server import Server
from mcp.types import Tool, TextContent
import os

import httpx
import oracledb
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

server = Server("oracle-tools")
pool = oracledb.create_pool(
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASS"],
    dsn=os.environ["DB_DSN"],
    min=1,
    max=4,
)


async def embed(text: str) -> list[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()["embedding"]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="vector_search",
            description="Semantic search over the knowledge base. Returns top-k passages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # Embed the query, then run an Oracle AI Vector Search against the indexed corpus.
    vec = await embed(arguments["query"])
    with pool.acquire() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT chunk_text FROM kb_chunks
            ORDER BY VECTOR_DISTANCE(embedding, VECTOR(:q, 768, FLOAT32), COSINE)
            FETCH FIRST :k ROWS ONLY
        """,
            q=vec,
            k=arguments.get("k", 5),
        )
        return [TextContent(type="text", text=row[0]) for row in cur]
