from pydantic import BaseModel


class VoiceSession(BaseModel):
    """What the website needs to start a conversation: nothing else."""

    token: str
