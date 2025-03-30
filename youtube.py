from os import getenv
from fastapi import FastAPI, Depends
from agno.models.openai import OpenAIChat
from agno.agent import Agent, AgentMemory
from agno.knowledge.youtube import YouTubeKnowledgeBase, YouTubeReader
from agno.vectordb.qdrant import Qdrant
from dotenv import load_dotenv
from textwrap import dedent
from agno.tools.youtube import YouTubeTools
import json
import yt_dlp

load_dotenv()

# Create tool that extracts youtube videos from channel and let the agent try to clone the guy?
# or
# Insert all transcriptions to db under a collection and try to duplicate his behavior and knowledge
    # add instructions fro the agent
    # use cli_app to debug
# query_youtube -> summarize youtube video, create knowledge from transcripts, tag it -> query knowledge
# query_channel -> get all transcripts, tag them -> query knowledge

# PersonaClone
# index_channel -> get all transcripts, tag them -> query knowledge
# index_video -> summarize youtube video, create knowledge from transcripts, tag it -> query knowledge

# Workflow
# indexer - index folder (links, youtube, pdf, txt, webpages)
# Persona agent - use memory of indexed info to imitate the persona.

api_key = getenv("QDRANT_API_KEY")
qdrant_url = getenv("QDRANT_URL")

app = FastAPI()

def fetch_channel_videos(channel_name, max_videos=5):
    ydl_opts = {
        'extract_flat': True,
        'force_generic_extractor': True,
        'max_downloads': max_videos
    }
    
    channel_url = "https://www.youtube.com/@" + channel_name

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(channel_url, download=False)
        videos = []
        # Handle different channel URL formats
        if 'entries' in result:
            for entry in result["entries"]:
                for entry2 in entry["entries"]:
                    videos.append(entry2['url'])
        else:
            videos = [result['url']]
    
    return videos[:max_videos]


# For each knowledge base document insertion, set collection name and query by it.
# Vectordb will search for the current collection everytime. 
# agent.knowledge.vector_db.collection = "youtube-agno" - collection can also be set manually
# find a way to insert documents manually to the knowledge base.
# agent.knowledge.vector_db.insert()
# agent.knowledge.load_documents(documents=docs)
# Exclude duplicates - agent.knowledge.vector_db.doc_exists()
# Already implemented

def query_youtube_video(video_url: str, query: str, chat_history: json = {}, debug=False) -> str:
    agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        search_knowledge=True,
        memory=AgentMemory(),
        tools=[YouTubeTools()],
        show_tool_calls=True,
        add_history_to_messages=True,
        instructions=dedent("""\
            You are an expert YouTube content analyst with a keen eye for detail! 🎓
            Follow these steps for comprehensive video analysis:
            1. Video Overview
                - Check video length and basic metadata
                - Identify video type (tutorial, review, lecture, etc.)
                - Note the content structure
            2. Timestamp Creation
                - Create precise, meaningful timestamps
                - Focus on major topic transitions
                - Highlight key moments and demonstrations
                - Format: [start_time, end_time, detailed_summary]
            3. Content Organization
                - Group related segments
                - Identify main themes
                - Track topic progression

            Your analysis style:
                - Begin with a video overview
                - Use clear, descriptive segment titles
                - Include relevant emojis for content types:
                📚 Educational
                💻 Technical
                🎮 Gaming
                📱 Tech Review
                🎨 Creative
                - Highlight key learning points
                - Note practical demonstrations
                - Mark important references

            Quality Guidelines:
                - Verify timestamp accuracy
                - Avoid timestamp hallucination
                - Ensure comprehensive coverage
                - Maintain consistent detail level
                - Focus on valuable content markers
        """)
    )
    if debug:
        agent.cli_app()
    
    # Generate response based on the query and chat history
    prompt = f"""Given this video: {video_url} 
                answer this: {query}
                YOUR RESPONSE MUST ALWAYS fulfill ALL the instructions above.
            """
    if chat_history:
        prompt = f"Given this conversation history: {chat_history}\n and this video: \n{video_url}\n{query}"
    
    response = agent.print_response(prompt, markdown=True, messages=chat_history)
    return response

def query_youtube_video_with_knowledge(video_url: str, query: str, chat_history: json = {}) -> str:

    vector_db = Qdrant(collection="youtube-agno", url=qdrant_url, api_key=api_key)

    # Create a temporary knowledge base for the single video
    temp_knowledge_base = YouTubeKnowledgeBase(
        urls=[video_url],
        vector_db=vector_db,
        # add instructions
        reader=YouTubeReader(chunk=True),
    )
    
    # Load the video content without recreating the entire database
    temp_knowledge_base.load(recreate=False)
    
    # Create a temporary agent for this interaction
    agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        knowledge=temp_knowledge_base,
        search_knowledge=True,
    )
    
    # # Generate response based on the query and chat history
    prompt = f"{query}"
    if chat_history:
        prompt = f"Given this conversation history: {chat_history}\n{query}"
    
    response = agent.print_response(prompt, markdown=True, messages=chat_history)
    return response

def index_channel(channel_name, limit=10):
    vector_db = Qdrant(collection=channel_name, url=qdrant_url, api_key=api_key)

    try:
        if not vector_db.exists():
            channel_videos = fetch_channel_videos(channel_name, limit)
        else:
            channel_videos = []
    except Exception as e:
        channel_videos = fetch_channel_videos(channel_name)
    
    # Create a knowledge base with the PDFs from the data/pdfs directory
    knowledge_base = YouTubeKnowledgeBase(
        urls=channel_videos,
        vector_db=vector_db,
        reader=YouTubeReader(chunk=True),
    )
    knowledge_base.load(recreate=False)  # only once, comment it out after first run

    return knowledge_base

def query_youtube_channel(channel_name: str, query: str, chat_history: json = {}) -> str:
    """
    Function to interact with a YouTube video by asking questions about its content.
    
    Args:
        video_url (str): The URL of the YouTube video to analyze
        query (str): The question or prompt about the video
        chat_history (str): Previous conversation history (optional)
        
    Returns:
        str: AI response based on the video content
    """
    # Create a temporary agent for this interaction
    agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        knowledge=index_channel(channel_name),
        search_knowledge=True,
    )
    # Generate response based on the query and chat history
    prompt = f"{query}"
    if chat_history:
        prompt = f"Given this conversation history: {chat_history}\n{query}"
    
    response = agent.print_response(prompt, markdown=True, messages=chat_history)
    return response

query_youtube_channel("HealthyGamerGG", "What is the major focus of the knowledge provided?")
# query_youtube_video("https://www.youtube.com/watch?v=VBifDZwPiI4", """When answering, Think about who would watch a video like this, what questions he would like to answer by watching this video?
#             Then answer those questions using the information from the video.""")

# query_youtube_video("https://www.youtube.com/watch?v=VBifDZwPiI4", "You are HealthyGG the author of the video, you have access to his knowledge, your answer style is like his", debug=True)


@app.get("/chat/youtube-video/")
async def chat_with_youtube_video(video_url: str, query: str, chat_history: str = ""):
    """
    Endpoint to chat about a specific YouTube video.
    
    Args:
        video_url (str): The URL of the YouTube video to analyze
        query (str): The question or prompt about the video
        chat_history (str): Previous conversation history (optional)
        
    Returns:
        dict: Contains the AI response
    """
    try:
        response = query_youtube_video(video_url, query, json.loads(chat_history))
        return {"response": response, "status": "success"}
    except Exception as e:
        return {"response": f"Error processing request: {str(e)}", "status": "error"}

@app.get("/chat/youtube-channel/")
async def chat_with_youtube_channel(video_url: str, query: str, chat_history: str = ""):
    try:
        response = query_youtube_channel(video_url, query, json.loads(chat_history))
        return {"response": response, "status": "success"}
    except Exception as e:
        return {"response": f"Error processing request: {str(e)}", "status": "error"}

# use vectordb rerankerer
# add rapidapi endpoint?
# create chat with this agent for testing
# what is the text segmentation? how much tokens for each request?
# Does the prompt needs fine tuning?
#   1. Add rag step for getting the right context


