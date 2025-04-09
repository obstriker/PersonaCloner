import os
import argparse
from agno.agent import Agent, AgentMemory
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.wikipedia import WikipediaTools
from agno.playground import Playground, serve_playground_app
from agno.memory.db.sqlite import SqliteMemoryDb
from agno.vectordb.qdrant import Qdrant
from dotenv import load_dotenv
from indexer import index_folder
from prompts import description, instructions

# Load environment variables
load_dotenv()
API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
app = None

# Constants
AGENT_MEMORY_DB_FILE = "tmps/agent_memory.db"

def initialize_vector_db(directory_path):
    """Initialize the vector database."""
    return Qdrant(collection=directory_path, url=QDRANT_URL, api_key=API_KEY)

def initialize_knowledge_base(directory_path = "", vectordb = None):
    """Initialize the knowledge base."""
    if not vectordb:
        vectordb = initialize_vector_db(directory_path)
    return index_folder(directory_path, vectordb)

def create_agent(agent_knowledge, persona):
    """Create and return the Persona Clone Agent."""

    return Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[DuckDuckGoTools(), WikipediaTools()],
        description=description.format(persona_name=persona),
        instructions=instructions,
        memory=AgentMemory(
            db=SqliteMemoryDb(
                table_name="agent_memory",
                db_file=AGENT_MEMORY_DB_FILE,
            ),
            create_user_memories=True,
        ),
        add_history_to_messages=True,
        num_history_responses=3,
        knowledge=agent_knowledge,
        show_tool_calls=True,
        markdown=True,
        debug_mode=True,
        monitoring=True,
        name="Cloner agent",
        agent_id="cloner",
    )

def main():
    parser = argparse.ArgumentParser(description="Run the Persona Cloner.")
    parser.add_argument('--server', action='store_true', help='Run the FastAPI server.')
    parser.add_argument('--debug', action='store_true', help='Run the playground app in debug mode.')
    parser.add_argument('--persona', type=str, help='Name of the persona to load')
    args = parser.parse_args()

    vectordb = initialize_vector_db(args.persona)
    knowledge_base = initialize_knowledge_base(args.persona, vectordb)
    agent = create_agent(knowledge_base, args.persona)

    if args.server:
        pass
    elif args.debug:
        global app
        app = Playground(agents=[agent]).get_app()
        serve_playground_app("cloner:app", reload=True)
        pass
    else:
        agent.cli_app()

if __name__ == "__main__":
    main()