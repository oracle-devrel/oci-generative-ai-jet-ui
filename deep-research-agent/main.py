"""
Oracle 26AI Deep Research Agent - Demo
"""

import oracledb
import openai
import os
import json
import hashlib
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from .env
CONFIG = {
    "ORACLE_USER": os.getenv("ORACLE_USER"),
    "ORACLE_PASSWORD": os.getenv("ORACLE_PASSWORD"),
    "ORACLE_DSN": os.getenv("ORACLE_DSN"),
    "ORACLE_WALLET_LOCATION": os.getenv("ORACLE_WALLET_LOCATION"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
}

print("📋 Configuration loaded:")
print(f"   User: {CONFIG['ORACLE_USER']}")
print(f"   DSN: {CONFIG['ORACLE_DSN']}")
print(f"   Wallet: {CONFIG['ORACLE_WALLET_LOCATION']}")


def connect():
    """Connect to Oracle 26AI."""
    print("\n🔌 Connecting to Oracle 26AI...")
    
    conn = oracledb.connect(
        user=CONFIG["ORACLE_USER"],
        password=CONFIG["ORACLE_PASSWORD"],
        dsn=CONFIG["ORACLE_DSN"],
        config_dir=CONFIG["ORACLE_WALLET_LOCATION"],
        wallet_location=CONFIG["ORACLE_WALLET_LOCATION"]
    )
    
    print(f"✅ Connected to Oracle AI Database")
    print(f"   Version: {conn.version}")
    return conn


def get_embedding(text):
    """Generate embedding using OpenAI."""
    client = openai.OpenAI(api_key=CONFIG["OPENAI_API_KEY"])
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def setup_schema(conn):
    """Create tables with VECTOR data type."""
    cursor = conn.cursor()
    
    print("\n📊 Setting up database schema...")
    
    # Drop existing table
    try:
        cursor.execute("DROP TABLE RESEARCH_MEMORY CASCADE CONSTRAINTS")
        print("   Dropped existing table")
    except:
        pass
    
    # Create table with VECTOR column
    cursor.execute("""
        CREATE TABLE RESEARCH_MEMORY (
            id VARCHAR2(64) PRIMARY KEY,
            query_text CLOB NOT NULL,
            query_embedding VECTOR(1536, FLOAT32),
            response_text CLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ Created RESEARCH_MEMORY table with VECTOR column")
    
    # Create HNSW index
    cursor.execute("""
        CREATE VECTOR INDEX idx_memory_embedding 
        ON RESEARCH_MEMORY(query_embedding)
        ORGANIZATION NEIGHBOR PARTITIONS
        WITH DISTANCE COSINE
        WITH TARGET ACCURACY 95
    """)
    print("   ✅ Created HNSW vector index")
    
    conn.commit()
    print("   ✅ Schema setup complete!")


def store_memory(conn, query, response):
    """Store a query with its embedding."""
    cursor = conn.cursor()
    
    memory_id = hashlib.sha256(
        (query + str(datetime.now())).encode()
    ).hexdigest()[:64]
    
    print(f"\n💾 Storing memory...")
    embedding = get_embedding(query)
    print(f"   Generated embedding ({len(embedding)} dimensions)")
    
    # Convert embedding to string format for Oracle
    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
    
    cursor.execute("""
        INSERT INTO RESEARCH_MEMORY 
        (id, query_text, query_embedding, response_text)
        VALUES (:1, :2, TO_VECTOR(:3), :4)
    """, [memory_id, query, embedding_str, response])
    
    conn.commit()
    print(f"   ✅ Stored: {memory_id[:12]}...")
    return memory_id


def search_memory(conn, query, limit=5):
    """Vector similarity search - THE MAGIC!"""
    cursor = conn.cursor()
    
    print(f"\n🔍 Searching memory for: '{query[:50]}...'")
    embedding = get_embedding(query)
    
    # Convert embedding to string format for Oracle
    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
    
    cursor.execute("""
        SELECT 
            id,
            query_text,
            response_text,
            VECTOR_DISTANCE(query_embedding, TO_VECTOR(:1), COSINE) as distance
        FROM RESEARCH_MEMORY
        WHERE query_embedding IS NOT NULL
        ORDER BY distance ASC
        FETCH FIRST :2 ROWS ONLY
    """, [embedding_str, limit])
    
    results = []
    for row in cursor:
        # Read CLOB fields properly
        query_text = row[1].read() if hasattr(row[1], 'read') else row[1]
        response_text = row[2].read() if hasattr(row[2], 'read') else row[2]
        
        similarity = round(1 - row[3], 3) if row[3] else 0
        results.append({
            "id": row[0],
            "query": query_text,
            "response": response_text,
            "similarity": similarity
        })
    
    return results


def research(conn, query):
    """Research with memory."""
    print(f"\n{'='*60}")
    print(f"🔬 RESEARCHING: {query}")
    print(f"{'='*60}")
    
    # Check memory first
    print("\n📚 Step 1: Checking memory...")
    memories = search_memory(conn, query)
    
    relevant = [m for m in memories if m["similarity"] > 0.7]
    if relevant:
        print(f"   ✅ Found {len(relevant)} relevant memories!")
        for m in relevant:
            print(f"      • '{m['query'][:40]}...' (similarity: {m['similarity']})")
    else:
        print("   ℹ️  No highly relevant memories found")
    
    # Generate response (simulated)
    print("\n🧠 Step 2: Generating response...")
    response = f"Analysis of '{query}': Key findings include emerging trends and developments in this area."
    
    # Store in memory
    print("\n💾 Step 3: Storing in memory...")
    store_memory(conn, query, response)
    
    print(f"\n✅ Research complete and memorized!")
    return response


def main():
    """Run the demo."""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     DEEP RESEARCH AGENT WITH ORACLE 26AI                  ║
    ║     ─────────────────────────────────────                 ║
    ║     One Database • Native Vectors • Persistent Memory     ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Connect
    conn = connect()
    
    # Setup schema
    setup_schema(conn)
    
    # Demo: First research query
    research(conn, "What are the latest developments in quantum computing?")
    
    # Demo: Related query (should find memory!)
    research(conn, "How does quantum computing affect cryptography and security?")
    
    # Demo: Different topic
    research(conn, "Best practices for building production AI agents")
    
    # Show memory recall
    print(f"\n{'='*60}")
    print("🧠 FINAL: Memory Recall for 'quantum'")
    print(f"{'='*60}")
    
    results = search_memory(conn, "quantum computing applications")
    for r in results:
        print(f"   • '{r['query'][:45]}...' → similarity: {r['similarity']}")
    
    # Stats
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM RESEARCH_MEMORY")
    count = cursor.fetchone()[0]
    print(f"\n📊 Total memories stored: {count}")
    
    conn.close()
    print("\n✅ Demo complete! Connection closed.")


if __name__ == "__main__":
    main()
