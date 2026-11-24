"""The website's voice demo. Public: customers don't log in."""

from fastapi import APIRouter, Response

from api.v1.deps import HttpClient
from schemas.voice import VoiceSession
from services import voice

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/session", response_model=VoiceSession)
async def create_session(http: HttpClient, response: Response) -> VoiceSession:
    """A single-use token to talk to the agent from the browser (expires in minutes)."""
    token = await voice.create_conversation_token(http)
    response.headers["Cache-Control"] = "no-store"
    return VoiceSession(token=token)
