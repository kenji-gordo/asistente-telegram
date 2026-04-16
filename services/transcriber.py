import logging
import asyncio
import tempfile
from pathlib import Path
from groq import Groq
from config.settings import settings

logger = logging.getLogger(__name__)


class Transcriber:
    """Service for transcribing audio using Whisper via Groq API"""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> Groq:
        """Get or create Groq client"""
        if self._client is None:
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY not configured")
            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    async def transcribe_audio(self, audio_path: str | Path) -> str:
        """
        Transcribe an audio file to text using Whisper

        Args:
            audio_path: Path to the audio file (ogg, mp3, wav, etc.)

        Returns:
            Transcribed text

        Raises:
            Exception: If transcription fails
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        def _transcribe():
            with open(audio_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    language="es"
                )
            return transcription.text.strip()

        try:
            text = await asyncio.to_thread(_transcribe)
            logger.info(f"Transcribed audio: {len(text)} chars")
            return text

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise Exception(f"Failed to transcribe audio: {e}")


transcriber = Transcriber()