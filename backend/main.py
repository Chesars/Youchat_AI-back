from fastapi import FastAPI, HTTPException, Request
from youtube_transcript_api import YouTubeTranscriptApi
from typing import Optional
from pydantic import BaseModel
import re
import httpx
from google import genai
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Replace hardcoded API key with environment variable
api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("API_KEY is not set in the environment variables")

# Define request/response models
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: dict

class TranscriptResponse(BaseModel):
    video_id: str
    transcript: str

app = FastAPI(
    title="YouChat AI API",
    description="""
    An AI-powered chat application that can understand and discuss YouTube videos.
    
    Features:
    - Extract transcripts from YouTube videos
    - Chat about video content using Google's Gemini AI
    - Handle follow-up questions about videos
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to restrict origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session state for storing transcripts
session_state = {}

@app.get(
    "/transcript/",
    response_model=TranscriptResponse,
    tags=["Transcripts"],
    summary="Get YouTube Video Transcript",
    description="Extracts the transcript from a YouTube video given its ID."
)
def get_transcript(
    video_id: str = "dQw4w9WgXcQ"  # Example video ID as default
) -> TranscriptResponse:
    """
    Get the transcript of a YouTube video.

    Args:
        video_id: The YouTube video ID (e.g., dQw4w9WgXcQ from youtube.com/watch?v=dQw4w9WgXcQ)

    Returns:
        A dictionary containing the video ID and its transcript

    Raises:
        HTTPException: If the video ID is invalid or transcript cannot be retrieved
    """
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry['text'] for entry in transcript])
        return {"video_id": video_id, "transcript": transcript_text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post(
    "/chat/",
    response_model=ChatResponse,
    tags=["Chat"],
    summary="Chat with AI about Videos",
    description="Send a message to chat with the AI. Include a YouTube URL to discuss specific videos."
)
async def chat(request: Request) -> ChatResponse:
    """
    Chat with the AI about videos or general topics.

    The endpoint handles:
    1. YouTube video links - extracts and analyzes the transcript
    2. Follow-up questions about previously discussed videos
    3. General questions (fallback to regular chat)

    Request body should contain a 'message' field with the user's input.
    """
    data = await request.json()
    message = data.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    # Check if the message contains a YouTube link
    video_id = extract_video_id(message)
    if video_id:
        try:
            # Fetch the transcript using the internal /transcript/ endpoint
            transcript = await call_transcript_api(video_id)
            session_state["transcript"] = transcript
            return {"reply": {"role": "assistant", "content": "I've retrieved the transcript. What would you like to ask?"}}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch transcript: {str(e)}")

    # Handle follow-up questions
    transcript = session_state.get("transcript")
    if transcript:
        try:
            reply = call_gemini_api(message, transcript)
            return {"reply": {"role": "assistant", "content": reply}}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to call Gemini API: {str(e)}")

    # Fallback to calling Gemini directly without transcript
    try:
        reply = call_gemini_api(message)
        return {"reply": {"role": "assistant", "content": reply}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to call Gemini API: {str(e)}")

def extract_video_id(message: str) -> Optional[str]:
    """Extract YouTube video ID from a message containing a URL."""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", message)
    return match.group(1) if match else None

async def call_transcript_api(video_id: str) -> str:
    """Internal helper to fetch transcript using the transcript endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://127.0.0.1:8000/transcript/?video_id={video_id}")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json().get("transcript")

def call_gemini_api(prompt: str, context: Optional[str] = None) -> str:
    """Call the Google Gemini API with optional context from video transcript."""
    # Initialize the GenAI client with your API key
    client = genai.Client(api_key=api_key)
    
    # Combine the context and prompt if context is provided
    full_prompt = f"{context}\n\n{prompt}" if context else prompt
    
    # Call the Gemini model to generate content
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=full_prompt,
    )
    
    # Return the generated text
    return response.text