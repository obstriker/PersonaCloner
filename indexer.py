import os
import typer
from agno.knowledge.url import UrlKnowledge
from pathlib import Path
from agno.knowledge.combined import CombinedKnowledgeBase
from agno.knowledge.csv import CSVKnowledgeBase
from agno.knowledge.json import JSONKnowledgeBase
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.knowledge.text import TextKnowledgeBase
from agno.knowledge.youtube import YouTubeKnowledgeBase, YouTubeReader
from youtube import fetch_channel_videos
from agno.vectordb.qdrant import Qdrant
from urllib.parse import urlparse, parse_qs
from os import getenv
from dotenv import load_dotenv
import json

load_dotenv()

# Retrieving book (RAG) doesnt work well.

api_key = getenv("QDRANT_API_KEY")
qdrant_url = getenv("QDRANT_URL")

def get_youtube_video_id(url):
    """
    Extract the video ID from a YouTube URL.
    Supports standard, short, and embed URLs.
    """
    parsed_url = urlparse(url)

    # Standard URL: https://www.youtube.com/watch?v=VIDEO_ID
    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        if parsed_url.path == "/watch":
            return parse_qs(parsed_url.query).get("v", [None])[0]
        elif parsed_url.path.startswith("/embed/"):
            return parsed_url.path.split("/embed/")[1]
        elif parsed_url.path.startswith("/v/"):
            return parsed_url.path.split("/v/")[1]

    # Shortened URL: https://youtu.be/VIDEO_ID
    elif parsed_url.hostname == "youtu.be":
        return parsed_url.path.lstrip("/")

    return None

def index_folder2(directory_path):
    if directory_path.endswith('.yt'):
        channel_videos = open(directory_path).readlines()

    knowledge_base = CombinedKnowledgeBase(
    sources=[
        PDFKnowledgeBase(
            vector_db=Qdrant(collection=directory_path, url=qdrant_url, api_key=api_key), path=directory_path
        ),
        CSVKnowledgeBase(
            vector_db=Qdrant(collection=directory_path, url=qdrant_url, api_key=api_key), path=directory_path
        ),
        JSONKnowledgeBase(
            vector_db=Qdrant(collection=directory_path, url=qdrant_url, api_key=api_key), path=directory_path
        ),
        TextKnowledgeBase(
            vector_db=Qdrant(collection=directory_path, url=qdrant_url, api_key=api_key), path=directory_path
        ),
        YouTubeKnowledgeBase(
            vector_db=Qdrant(collection=directory_path, url=qdrant_url, api_key=api_key), urls=channel_videos,
    )
    ],
    vector_db=Qdrant(collection=directory_path, url=qdrant_url, api_key=api_key),
)

def read_persona_json(file_path):
    with open(file_path, 'r') as f:
        persona_data = json.load(f)
    return persona_data

def index_persona_resources(persona_data, vector_db):
    #if not vector_db.exists()
    knowledge_bases = []

    # Index YouTube channels
    if persona_data['sources'].get("youtube"):
        channel_name = persona_data['sources']['youtube']['channel_name']
        knowledge_bases.append(index_channel(channel_name, vector_db))

        if persona_data['sources']["youtube"].get("videos"):
            knowledge_bases.append(index_urls(channel_name, vector_db))

    # Index website URLs
    if persona_data['sources'].get("website"):
        urls = persona_data['sources']['website']['urls']
        for url in urls:
            knowledge_bases.append(index_urls(url))

    # Index files (PDF, text, CSV, JSON)
    if persona_data['sources'].get("files"):
        for file_type, details in persona_data['sources']['files'].items():
            path = details['path']
            if os.path.exists(path):
                knowledge_bases.append(index_folder(path, vector_db))

    knowledge_bases.remove(None)
    return combine_agent_knowledge(knowledge_bases, vector_db)

def combine_agent_knowledge(kn, vectordb):
    knowledge_base = CombinedKnowledgeBase(
        sources = [k for k in kn],
        vector_db = vectordb
    )
    knowledge_base.load(recreate=False, skip_existing=True)

    return knowledge_base

def index_folder(directory_path, vectordb=None):
    knowledge_bases = []

    if directory_path and os.path.exists(directory_path + "/persona.json"):
        persona_data = read_persona_json(directory_path + "/persona.json")
        knowledge_bases.append(index_persona_resources(persona_data, vectordb))
    else:
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                if file.endswith('.pdf'):
                    knowledge_bases.append(index_pdf(file_path, vectordb))
                elif file.endswith('.txt'):
                    knowledge_bases.append(index_txt(file_path, vectordb))
                elif file.endswith('.urls'):
                    with open(file_path, "r") as f:
                        lines = f.readlines()
                        knowledge = index_urls([line.replace('\n', '') for line in lines], vectordb)
                        knowledge_bases.append(knowledge)
                elif file.endswith('.yt'):
                    with open(file_path, "r") as f:
                        lines = f.readlines()
                        knowledge = index_urls([line.replace('\n', '') for line in lines], vectordb)
                        knowledge_bases.append(knowledge)
                elif file.endswith('.ytc'):
                    with open(file_path, "r") as f:
                        channels = f.readlines()
                        for channel in channels:
                            knowledge = index_channel(channel.replace('\n', ''), vectordb)
                            knowledge_bases.append(knowledge)

    return combine_agent_knowledge(knowledge_bases, vectordb)

def index_pdf(file_path, vectordb):
    agent_knowledge = PDFKnowledgeBase(
            collection=file_path,
            vector_db=vectordb, path=file_path
        )
    
    agent_knowledge.load(recreate=False)
    return agent_knowledge

def index_txt(file_path, vectordb):
    agent_knowledge = TextKnowledgeBase(
        collection=file_path,
        path=Path(file_path),
        vector_db=vectordb,
    )

    agent_knowledge.load(recreate=False)
    return agent_knowledge

def index_urls(url, vectordb=None):
    if not isinstance(url, list):
        urls = [url]
    else:
        urls = url

    youtube_urls = []
    website_urls = []

    for url in urls:
        if "youtube.com" in url:
            youtube_urls.append(url)
        else:
            website_urls.append(url)

    if len(youtube_urls) > 0:
        if not vectordb.name_exists(get_youtube_video_id("youtube" + url)):
            agent_knowledge = YouTubeKnowledgeBase(
                collection=url,
                urls=youtube_urls,
                vector_db=vectordb,
            )
            agent_knowledge.load(recreate=False, skip_existing=True)

    if len(website_urls) > 0:
        agent_knowledge = UrlKnowledge(
            collection=url,
            urls=website_urls,
            vector_db=vectordb,
        )

        agent_knowledge.load(recreate=False, skip_existing=True)
    return agent_knowledge


def index_channel(channel_name, vectordb, limit=10):    
    print("Indexing channel:", channel_name)
    
    try:
        if not vectordb.exists():
            channel_videos = fetch_channel_videos(channel_name, limit)
        else:
            channel_videos = []
    except Exception as e:
        channel_videos = []
        print("Failed to index channel:", e)
        pass
    
    # Create a knowledge base with the PDFs from the data/pdfs directory

    if channel_videos:
        knowledge_base = YouTubeKnowledgeBase(
            urls=channel_videos,
            vector_db=vectordb,
            reader=YouTubeReader(chunk=True),
        )
        
        knowledge_base.load()
        return knowledge_base
    
    return None

if __name__ == "__main__":
    typer.run(index_folder)