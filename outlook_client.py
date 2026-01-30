"""Outlook Calendar client using ICS feed."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

import requests
from icalendar import Calendar

import config

logger = logging.getLogger(__name__)


class OutlookClient:
    """Client for accessing Outlook Calendar via published ICS feed."""

    def __init__(self):
        self.ics_url = config.OUTLOOK_ICS_URL

    def authenticate(self) -> bool:
        """Verify that we can access the ICS feed."""
        if not self.ics_url:
            logger.error(
                "OUTLOOK_ICS_URL not configured. "
                "Get it from Outlook Web: Settings → Calendar → Shared calendars → Publish a calendar"
            )
            return False

        try:
            response = requests.head(self.ics_url, timeout=10)
            if response.status_code == 200:
                logger.info("Successfully connected to Outlook ICS feed")
                return True
            else:
                logger.error(f"ICS feed returned status {response.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"Failed to connect to ICS feed: {e}")
            return False

    def get_calendar_events(
        self,
        days_back: int = config.SYNC_DAYS_BACK,
        days_ahead: int = config.SYNC_DAYS_AHEAD,
    ) -> list[dict]:
        """Fetch calendar events from Outlook ICS feed."""
        try:
            response = requests.get(self.ics_url, timeout=60)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch ICS feed: {e}")
            return []

        try:
            cal = Calendar.from_ical(response.content)
        except Exception as e:
            logger.error(f"Failed to parse ICS data: {e}")
            return []

        # Calculate date range
        now = datetime.now()
        start_date = now - timedelta(days=days_back)
        end_date = now + timedelta(days=days_ahead)

        events = []
        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            event = self._parse_event(component)
            if event and self._is_in_range(event, start_date, end_date):
                events.append(event)

        # Sort by start time
        events.sort(key=lambda e: e["start"])
        logger.info(f"Found {len(events)} events in date range")
        return events

    def _parse_event(self, component) -> Optional[dict]:
        """Parse an ICS VEVENT component into our event format."""
        try:
            # Get unique ID
            uid = str(component.get("uid", ""))
            if not uid:
                return None

            # Get title
            title = str(component.get("summary", "(Ingen tittel)"))

            # Get start/end times
            dtstart = component.get("dtstart")
            dtend = component.get("dtend")

            if not dtstart:
                return None

            # Determine if all-day event
            is_all_day = not hasattr(dtstart.dt, "hour")

            # Convert to datetime strings
            if is_all_day:
                start_str = dtstart.dt.isoformat()
                end_str = dtend.dt.isoformat() if dtend else start_str
            else:
                start_dt = dtstart.dt
                end_dt = dtend.dt if dtend else start_dt

                # Handle timezone-aware datetimes
                if hasattr(start_dt, "isoformat"):
                    start_str = start_dt.isoformat()
                    end_str = end_dt.isoformat()
                else:
                    start_str = str(start_dt)
                    end_str = str(end_dt)

            # Get organizer
            organizer = component.get("organizer")
            organizer_name = "Ukjent"
            organizer_email = ""
            if organizer:
                organizer_email = str(organizer).replace("mailto:", "")
                if hasattr(organizer, "params") and "CN" in organizer.params:
                    organizer_name = organizer.params["CN"]
                else:
                    organizer_name = organizer_email.split("@")[0]

            # Get location
            location = component.get("location")
            location_str = str(location) if location else ""

            # Get description/body
            description = component.get("description")
            body = str(description)[:1000] if description else ""

            # Get categories
            categories_prop = component.get("categories")
            categories = []
            if categories_prop:
                if hasattr(categories_prop, "cats"):
                    categories = [str(c) for c in categories_prop.cats]
                else:
                    categories = [str(categories_prop)]

            # Get last modified
            last_modified = component.get("last-modified")
            last_modified_str = ""
            if last_modified:
                last_modified_str = last_modified.dt.isoformat()

            # Get status
            status = str(component.get("status", "CONFIRMED")).lower()
            if status == "cancelled":
                return None  # Skip cancelled events

            # Check if recurring
            rrule = component.get("rrule")
            recurrence_id = component.get("recurrence-id")
            is_recurring = rrule is not None or recurrence_id is not None

            # Create stable ID from UID (hash to avoid special characters)
            stable_id = hashlib.sha256(uid.encode()).hexdigest()[:32]

            return {
                "id": stable_id,
                "original_uid": uid,
                "title": title,
                "start": start_str,
                "end": end_str,
                "timezone": "Europe/Oslo",
                "location": location_str,
                "organizer": organizer_name,
                "organizer_email": organizer_email,
                "body": body,
                "categories": categories,
                "is_all_day": is_all_day,
                "is_recurring": is_recurring,
                "status": status,
                "last_modified": last_modified_str,
            }

        except Exception as e:
            logger.warning(f"Failed to parse event: {e}")
            return None

    def _is_in_range(self, event: dict, start_date: datetime, end_date: datetime) -> bool:
        """Check if event falls within the date range."""
        try:
            event_start = event["start"]

            # Parse date from ISO format
            if "T" in event_start:
                event_dt = datetime.fromisoformat(event_start.replace("Z", "+00:00"))
                # Convert to naive datetime for comparison
                if event_dt.tzinfo:
                    event_dt = event_dt.replace(tzinfo=None)
            else:
                event_dt = datetime.fromisoformat(event_start)

            return start_date <= event_dt <= end_date

        except Exception as e:
            logger.warning(f"Failed to check date range for event: {e}")
            return True  # Include if we can't determine


def main():
    """Test the Outlook client."""
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    logging.basicConfig(level=logging.INFO)

    client = OutlookClient()
    if not client.authenticate():
        print("Failed to connect to ICS feed!")
        return

    print("\nFetching calendar events...")
    events = client.get_calendar_events(days_back=7, days_ahead=14)

    print(f"\nFound {len(events)} events:\n")
    for event in events[:10]:
        print(f"- {event['title']}")
        print(f"  {event['start']} - {event['end']}")
        print(f"  Organizer: {event['organizer']}")
        print()


if __name__ == "__main__":
    main()
