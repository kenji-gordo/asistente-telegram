import logging
import asyncio
from datetime import timedelta
from google.oauth2 import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from models.event import Event
from config.settings import settings

logger = logging.getLogger(__name__)

# Google Calendar API scopes
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    """Service for interacting with Google Calendar API"""

    def __init__(self):
        self._service = None
        self._credentials = None

    def _get_credentials(self):
        """Load or refresh Google OAuth credentials"""
        if self._credentials is None:
            creds = None
            creds_file = settings.CREDENTIALS_PATH

            # Check if token file exists
            token_file = creds_file.parent / "token.json"
            if token_file.exists():
                from google.oauth2.credentials import Credentials
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

            # If no valid credentials, run OAuth flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh()
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(creds_file), SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save for next time
                with open(token_file, "w") as token:
                    token.write(creds.to_json())

            self._credentials = creds

        return self._credentials

    @property
    def service(self):
        """Get or create Google Calendar service"""
        if self._service is None:
            creds = self._get_credentials()
            self._service = build("calendar", "v3", credentials=creds)
        return self._service

    async def create_event(self, event: Event) -> dict:
        """
        Create a new event in Google Calendar

        Args:
            event: Event object with event data

        Returns:
            Created event dict from API

        Raises:
            Exception: If event creation fails
        """
        if not event.title:
            raise ValueError("Event must have a title")

        # Build description with category info
        description = event.description or ""
        if event.category and event.category != "general":
            category_label = f"[{event.category.upper()}]"
            if event.course:
                category_label += f" ({event.course})"
            if event.event_type:
                category_label += f" - {event.event_type.upper()}"
            description = f"{category_label}\n{description}".strip()

        event_body = {
            "summary": event.title,
            "description": description,
        }

        if event.start_time:
            event_body["start"] = {
                "dateTime": event.start_time.isoformat(),
                "timeZone": "America/Argentina/Buenos_Aires",
            }

            if event.end_time:
                event_body["end"] = {
                    "dateTime": event.end_time.isoformat(),
                    "timeZone": "America/Argentina/Buenos_Aires",
                }
            else:
                # Default 1 hour duration
                event_body["end"] = {
                    "dateTime": (event.start_time + timedelta(hours=1)).isoformat(),
                    "timeZone": "America/Argentina/Buenos_Aires",
                }

        if event.reminder_minutes:
            event_body["reminders"] = {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": event.reminder_minutes}
                ],
            }

        def _call_calendar_api():
            return self.service.events().insert(
                calendarId=settings.GOOGLE_CALENDAR_ID,
                body=event_body
            ).execute()

        try:
            created = await asyncio.to_thread(_call_calendar_api)

            logger.info(f"Created event: {created['id']}")
            return created

        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            raise Exception(f"Failed to create calendar event: {e}")


calendar_service = CalendarService()