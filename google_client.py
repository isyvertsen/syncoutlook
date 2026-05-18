"""Google Calendar API client."""

import logging
import os
from datetime import datetime
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

logger = logging.getLogger(__name__)


class GoogleCalendarClient:
    """Client for accessing Google Calendar API."""

    # Custom property to link events to Outlook
    OUTLOOK_ID_PROPERTY = "outlookEventId"

    def __init__(self):
        self.creds: Optional[Credentials] = None
        self.service = None

    def authenticate(self) -> bool:
        """Authenticate with Google Calendar API using a service account."""
        if not os.path.exists(config.GOOGLE_SERVICE_ACCOUNT_FILE):
            logger.error(
                f"Service account key not found: {config.GOOGLE_SERVICE_ACCOUNT_FILE}\n"
                "Create a service account in Google Cloud Console, download its "
                "JSON key, save it to this path, and share the target calendar "
                "with the service account's email ('Make changes to events')."
            )
            return False

        try:
            self.creds = service_account.Credentials.from_service_account_file(
                config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=config.GOOGLE_SCOPES
            )
            self.service = build("calendar", "v3", credentials=self.creds)
            logger.info("Successfully connected to Google Calendar API")
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with service account: {e}")
            return False

    def get_synced_events(self) -> dict[str, dict]:
        """Get all events that were synced from Outlook (have our custom property)."""
        if not self.service:
            if not self.authenticate():
                return {}

        synced_events = {}

        try:
            page_token = None
            while True:
                events_result = self.service.events().list(
                    calendarId=config.GOOGLE_CALENDAR_ID,
                    pageToken=page_token,
                    singleEvents=True,
                    maxResults=500,
                ).execute()

                for event in events_result.get("items", []):
                    outlook_id = event.get("extendedProperties", {}).get(
                        "private", {}
                    ).get(self.OUTLOOK_ID_PROPERTY)
                    if outlook_id:
                        synced_events[outlook_id] = event

                page_token = events_result.get("nextPageToken")
                if not page_token:
                    break

            logger.info(f"Found {len(synced_events)} previously synced events")
            return synced_events

        except HttpError as e:
            logger.error(f"Failed to fetch synced events: {e}")
            return {}

    def create_event(self, outlook_event: dict) -> Optional[str]:
        """Create a new event in Google Calendar."""
        if not self.service:
            if not self.authenticate():
                return None

        google_event = self._convert_to_google_event(outlook_event)

        try:
            created = self.service.events().insert(
                calendarId=config.GOOGLE_CALENDAR_ID,
                body=google_event,
            ).execute()

            logger.info(f"Created event: {outlook_event['title']}")
            return created.get("id")

        except HttpError as e:
            logger.error(f"Failed to create event '{outlook_event['title']}': {e}")
            return None

    def update_event(self, google_event_id: str, outlook_event: dict) -> bool:
        """Update an existing event in Google Calendar."""
        if not self.service:
            if not self.authenticate():
                return False

        google_event = self._convert_to_google_event(outlook_event)

        try:
            self.service.events().update(
                calendarId=config.GOOGLE_CALENDAR_ID,
                eventId=google_event_id,
                body=google_event,
            ).execute()

            logger.info(f"Updated event: {outlook_event['title']}")
            return True

        except HttpError as e:
            logger.error(f"Failed to update event '{outlook_event['title']}': {e}")
            return False

    def delete_event(self, google_event_id: str, event_title: str = "") -> bool:
        """Delete an event from Google Calendar."""
        if not self.service:
            if not self.authenticate():
                return False

        try:
            self.service.events().delete(
                calendarId=config.GOOGLE_CALENDAR_ID,
                eventId=google_event_id,
            ).execute()

            logger.info(f"Deleted event: {event_title or google_event_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Event already deleted: {event_title or google_event_id}")
                return True
            logger.error(f"Failed to delete event '{event_title}': {e}")
            return False

    def _convert_to_google_event(self, outlook_event: dict) -> dict:
        """Convert Outlook event format to Google Calendar format."""
        event = {
            "summary": outlook_event["title"],
            "description": self._build_description(outlook_event),
            "extendedProperties": {
                "private": {
                    self.OUTLOOK_ID_PROPERTY: outlook_event["id"],
                    "outlookLastModified": outlook_event.get("last_modified", ""),
                }
            },
        }

        # Add location if present
        if outlook_event.get("location"):
            event["location"] = outlook_event["location"]

        # Handle all-day vs timed events
        if outlook_event.get("is_all_day"):
            # All-day events use date instead of dateTime
            start_date = outlook_event["start"][:10]  # YYYY-MM-DD
            end_date = outlook_event["end"][:10]
            event["start"] = {"date": start_date}
            event["end"] = {"date": end_date}
        else:
            # Timed events
            event["start"] = {
                "dateTime": self._format_datetime(outlook_event["start"]),
                "timeZone": outlook_event.get("timezone", "Europe/Oslo"),
            }
            event["end"] = {
                "dateTime": self._format_datetime(outlook_event["end"]),
                "timeZone": outlook_event.get("timezone", "Europe/Oslo"),
            }

        # Add reminder before event
        if config.REMINDER_MINUTES > 0:
            event["reminders"] = {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": config.REMINDER_MINUTES}
                ]
            }

        return event

    def _format_datetime(self, dt_str: str) -> str:
        """Format datetime string for Google Calendar API."""
        # Remove microseconds if present and ensure proper format
        if "." in dt_str:
            dt_str = dt_str.split(".")[0]
        if not dt_str.endswith("Z") and "+" not in dt_str:
            dt_str += "Z"
        return dt_str

    def _build_description(self, outlook_event: dict) -> str:
        """Build event description with metadata."""
        parts = []

        if outlook_event.get("body"):
            parts.append(outlook_event["body"])

        parts.append("")
        parts.append("---")
        parts.append(f"Synkronisert fra Outlook")
        parts.append(f"Organisator: {outlook_event.get('organizer', 'Ukjent')}")

        if outlook_event.get("categories"):
            parts.append(f"Kategorier: {', '.join(outlook_event['categories'])}")

        return "\n".join(parts)


def main():
    """Test the Google Calendar client."""
    logging.basicConfig(level=logging.INFO)

    client = GoogleCalendarClient()
    if not client.authenticate():
        print("Authentication failed!")
        return

    print("\nFetching synced events...")
    synced = client.get_synced_events()
    print(f"Found {len(synced)} synced events")

    for outlook_id, event in list(synced.items())[:5]:
        print(f"- {event.get('summary', '(no title)')}")


if __name__ == "__main__":
    main()
