# Persona Cloner

## Overview
Persona Cloner is an AI-powered tool that can accurately mimic a specific person’s communication style, tone, and knowledge. By indexing a rich dataset—including folders of materials, PDFs, links, YouTube channels, YouTube videos and more—the bot builds a comprehensive profile of the individual.

## Example Output
![Example Output](photos/example_output.png)

In the example we can see a folder that includes a book and a JSON file describing the persona and its sources. The example persona can be found here:
```
{
    "name": "CodieSanchez",
    "sources": {
        "youtube": {
            "channel_name": "CodieSanchezCT"
        },
        "websites": {
            "urls": ["https://codiesanchez.com/"]
        },
        "files": {
            "pdf": {
                "path": "CodieSanchez/book.pdf"
            }
        }
    }
}
```

## Usage
To run the Persona Cloner, use the following command:
```bash
python cloner.py --persona "PersonaName" --server
```
- Use `--server` to run the FastAPI server.
- Use `--debug` to run the playground app in debug mode.

## Features
- **Agent Creation**: Create agents that can respond in the style of specified personas.
- **Knowledge Base Integration**: Utilize a vector database to store and retrieve knowledge relevant to the personas.
- **Tool Integration**: Access external tools such as DuckDuckGo and Wikipedia for enhanced responses.
- **Memory Management**: Retain memories from previous interactions to personalize user experiences.

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/PersonaCloner.git
   cd PersonaCloner
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables in a `.env` file:
   ```
   QDRANT_API_KEY=your_api_key
   QDRANT_URL=your_qdrant_url
   ```
