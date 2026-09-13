from main import connect, research, search_memory

def connect_to_oracle():
    return connect()

class DeepResearchAgent:
    def __init__(self, connection):
        self.conn = connection
    
    def research(self, query):
        return research(self.conn, query)
    
    def recall(self, query):
        results = search_memory(self.conn, query)
        print(f"Found {len(results)} memories:")
        for r in results:
            print(f"  • '{r['query'][:50]}...' (similarity: {r['similarity']})")

# Connect to Oracle 26AI
connection = connect_to_oracle()

# Initialize the agent
agent = DeepResearchAgent(connection)

# First research query
print("\n" + "="*50)
print("FIRST QUERY: Quantum Computing")
print("="*50)
agent.research("What are the latest developments in quantum computing?")

# Second research query (related topic)
print("\n" + "="*50)
print("SECOND QUERY: Related Topic")
print("="*50)
agent.research("How does quantum computing affect cryptography?")

# Memory recall
print("\n" + "="*50)
print("MEMORY RECALL")
print("="*50)
agent.recall("quantum")
