import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class Settings:
    """Application settings loaded from environment variables"""

    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "")
    CREDENTIALS_PATH: Path = PROJECT_ROOT / "credentials.json"
    GOOGLE_CREDENTIALS_JSON: str = os.getenv("GOOGLE_CREDENTIALS", "")
    GOOGLE_TOKEN_JSON: str = os.getenv("GOOGLE_TOKEN", "")

    def ensure_credentials(self):
        """Create credentials.json from env var if needed"""
        if self.GOOGLE_CREDENTIALS_JSON:
            try:
                creds_data = json.loads(self.GOOGLE_CREDENTIALS_JSON)
                with open(self.CREDENTIALS_PATH, "w") as f:
                    json.dump(creds_data, f, indent=2)
                logger.info(f"Credentials written to {self.CREDENTIALS_PATH}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid GOOGLE_CREDENTIALS JSON: {e}")
        else:
            logger.warning("GOOGLE_CREDENTIALS env var is empty")

    def get_credentials_path(self) -> Path:
        """Get credentials path, creating from env if needed"""
        self.ensure_credentials()
        return self.CREDENTIALS_PATH

    def get_token_path(self) -> Path:
        """Get token path, creating from env if needed"""
        token_file = self.CREDENTIALS_PATH.parent / "token.json"
        if not token_file.exists() and self.GOOGLE_TOKEN_JSON:
            try:
                token_data = json.loads(self.GOOGLE_TOKEN_JSON)
                with open(token_file, "w") as f:
                    json.dump(token_data, f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid GOOGLE_TOKEN JSON: {e}")
        return token_file


settings = Settings()
settings.ensure_credentials()