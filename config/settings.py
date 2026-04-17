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

    def ensure_credentials(self):
        """Create credentials.json from env var if needed"""
        if not self.CREDENTIALS_PATH.exists() and self.GOOGLE_CREDENTIALS_JSON:
            try:
                creds_data = json.loads(self.GOOGLE_CREDENTIALS_JSON)
                with open(self.CREDENTIALS_PATH, "w") as f:
                    json.dump(creds_data, f, indent=2)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid GOOGLE_CREDENTIALS JSON: {e}")

    def get_credentials_path(self) -> Path:
        """Get credentials path, creating from env if needed"""
        self.ensure_credentials()
        return self.CREDENTIALS_PATH


settings = Settings()
settings.ensure_credentials()