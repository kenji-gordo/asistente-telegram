import json
import os
from pathlib import Path
from dotenv import load_dotenv

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
        """Create credentials.json from env var if it doesn't exist"""
        if not self.CREDENTIALS_PATH.exists() and self.GOOGLE_CREDENTIALS_JSON:
            with open(self.CREDENTIALS_PATH, "w") as f:
                f.write(self.GOOGLE_CREDENTIALS_JSON)


settings = Settings()
settings.ensure_credentials()