import os
from pathlib import Path
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from dotenv import load_dotenv
from indexer import index_folder
from agno.agent import Agent, AgentMemory
from agno.memory.db.sqlite import SqliteMemoryDb
from textwrap import dedent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.wikipedia import WikipediaTools

load_dotenv()

# Load environment variables for Qdrant
api_key = os.getenv("QDRANT_API_KEY")
qdrant_url = os.getenv("QDRANT_URL")

# Example usage
if __name__ == "__main__":
    persona_folder = "CodieSanchez"  # Specify the path to the persona folder
    knowledge_base = index_folder(persona_folder)

    persona_name = "CodieSanchez"  # Example persona

    # Define the agent's instructions
    instructions = f"""\
    You are {persona_name}. You have access to his knowledge, your answer style is like his. Your task is to respond in his style.
    When given a query, you will generate responses that reflect their knowledge, tone, and style.
    Ensure that your responses are engaging, informative, and true to the persona's characteristics and knowledge.

    Instructions:
    1. Don't let the user know that you are a persona cloning agent.
    """

    # Initialize the Persona Clone Agent with the knowledge base
    agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[DuckDuckGoTools(), WikipediaTools()],
        description=dedent("""\
        You are a helpful and friendly persona cloner that mimics the style and knowledge of specified personas.
        """),
        instructions=instructions.format(persona_name),
        memory=AgentMemory(
            db=SqliteMemoryDb(
                table_name="agent_memory",
                db_file="tmp/agent_memory.db",
            ),
            create_user_memories=True,
        ),
        add_history_to_messages=True,
        num_history_responses=3,
        knowledge=knowledge_base,  # Pass the knowledge base to the agent
        show_tool_calls=True,
        markdown=True,
    )

    # Example interaction with the agent
    user_input = "What are your thoughts on the future of space travel?"
    agent.cli_app()
    # response = agent.print_response(f"Respond as {persona_name}: {user_input}", stream=True)
    # print(response)