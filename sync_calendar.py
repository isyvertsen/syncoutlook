#!/usr/bin/env python3
"""Main script for syncing Outlook calendar to Google Calendar with AI filtering."""

import argparse
import logging
import sys
from datetime import datetime

import holidays

import config
from ai_filter import AIFilter
from google_client import GoogleCalendarClient
from outlook_client import OutlookClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def is_working_hours() -> bool:
    """Check if current time is within working hours (weekdays 07:00-15:00, not holidays)."""
    now = datetime.now()

    # Check if it's a weekend (Saturday=5, Sunday=6)
    if now.weekday() >= 5:
        logger.info("Skipping sync: Weekend")
        return False

    # Check if it's a Norwegian public holiday
    no_holidays = holidays.Norway()
    if now.date() in no_holidays:
        holiday_name = no_holidays.get(now.date())
        logger.info(f"Skipping sync: Public holiday ({holiday_name})")
        return False

    # Check if it's within working hours (07:00-15:00)
    if now.hour < 7 or now.hour >= 15:
        logger.info(f"Skipping sync: Outside working hours (current: {now.hour}:00)")
        return False

    return True


class CalendarSync:
    """Main synchronization logic."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.outlook = OutlookClient()
        self.google = GoogleCalendarClient()
        self.ai_filter = AIFilter()

        # Statistics
        self.stats = {
            "outlook_events": 0,
            "filtered_in": 0,
            "filtered_out": 0,
            "created": 0,
            "updated": 0,
            "deleted": 0,
            "errors": 0,
        }

    def run(self) -> bool:
        """Run the synchronization process."""
        logger.info("=" * 60)
        logger.info(f"Starting calendar sync at {datetime.now()}")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info("=" * 60)

        # Step 1: Authenticate with both services
        if not self._authenticate():
            return False

        # Step 2: Fetch events from Outlook
        outlook_events = self._fetch_outlook_events()
        if outlook_events is None:
            return False

        # Step 3: Filter events using AI
        events_to_sync = self._filter_events(outlook_events)

        # Step 4: Get existing synced events from Google
        google_synced = self.google.get_synced_events()

        # Step 5: Synchronize events
        self._sync_events(events_to_sync, google_synced, outlook_events)

        # Step 6: Print summary
        self._print_summary()

        return self.stats["errors"] == 0

    def _authenticate(self) -> bool:
        """Authenticate with Outlook and Google."""
        logger.info("Authenticating with Outlook...")
        if not self.outlook.authenticate():
            logger.error("Failed to authenticate with Outlook")
            return False

        logger.info("Authenticating with Google Calendar...")
        if not self.google.authenticate():
            logger.error("Failed to authenticate with Google Calendar")
            return False

        return True

    def _fetch_outlook_events(self) -> list[dict] | None:
        """Fetch events from Outlook."""
        logger.info(
            f"Fetching Outlook events ({config.SYNC_DAYS_BACK} days back, "
            f"{config.SYNC_DAYS_AHEAD} days ahead)..."
        )

        events = self.outlook.get_calendar_events(
            days_back=config.SYNC_DAYS_BACK,
            days_ahead=config.SYNC_DAYS_AHEAD,
        )

        if events is None:
            logger.error("Failed to fetch Outlook events")
            return None

        self.stats["outlook_events"] = len(events)
        logger.info(f"Found {len(events)} events in Outlook")
        return events

    def _filter_events(self, events: list[dict]) -> list[tuple[dict, str]]:
        """Filter events using AI."""
        logger.info("Filtering events using AI...")

        filtered = self.ai_filter.filter_events(events)

        self.stats["filtered_in"] = len(filtered)
        self.stats["filtered_out"] = len(events) - len(filtered)

        logger.info(
            f"AI filtering: {len(filtered)} to sync, "
            f"{len(events) - len(filtered)} skipped"
        )
        return filtered

    def _sync_events(
        self,
        events_to_sync: list[tuple[dict, str]],
        google_synced: dict[str, dict],
        all_outlook_events: list[dict],
    ):
        """Synchronize events to Google Calendar."""
        logger.info("Syncing events to Google Calendar...")

        # Build set of Outlook IDs that should be synced
        outlook_ids_to_sync = {event["id"] for event, _ in events_to_sync}

        # Build set of all current Outlook IDs
        all_outlook_ids = {event["id"] for event in all_outlook_events}

        # Create or update events
        for event, reason in events_to_sync:
            outlook_id = event["id"]

            if outlook_id in google_synced:
                # Event exists - check if update needed
                google_event = google_synced[outlook_id]
                if self._needs_update(event, google_event):
                    self._update_event(google_event["id"], event)
                else:
                    logger.debug(f"No update needed: {event['title']}")
            else:
                # New event - create it
                self._create_event(event, reason)

        # Delete events that are no longer in Outlook or no longer pass filter
        for outlook_id, google_event in google_synced.items():
            if outlook_id not in all_outlook_ids:
                # Event was deleted from Outlook
                self._delete_event(
                    google_event["id"],
                    google_event.get("summary", "Unknown"),
                    "Deleted from Outlook",
                )
            elif outlook_id not in outlook_ids_to_sync:
                # Event exists but no longer passes AI filter
                self._delete_event(
                    google_event["id"],
                    google_event.get("summary", "Unknown"),
                    "No longer passes AI filter",
                )

    def _needs_update(self, outlook_event: dict, google_event: dict) -> bool:
        """Check if Google event needs to be updated."""
        # Compare last modified timestamps
        outlook_modified = outlook_event.get("last_modified", "")
        google_props = google_event.get("extendedProperties", {}).get("private", {})
        cached_modified = google_props.get("outlookLastModified", "")

        if outlook_modified and cached_modified:
            return outlook_modified > cached_modified

        # If no timestamps, compare basic fields
        if outlook_event["title"] != google_event.get("summary", ""):
            return True

        return False

    def _create_event(self, event: dict, reason: str):
        """Create a new event in Google Calendar."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create: {event['title']}")
            logger.info(f"          Reason: {reason}")
            self.stats["created"] += 1
            return

        result = self.google.create_event(event)
        if result:
            self.stats["created"] += 1
        else:
            self.stats["errors"] += 1

    def _update_event(self, google_id: str, event: dict):
        """Update an existing event in Google Calendar."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would update: {event['title']}")
            self.stats["updated"] += 1
            return

        if self.google.update_event(google_id, event):
            self.stats["updated"] += 1
        else:
            self.stats["errors"] += 1

    def _delete_event(self, google_id: str, title: str, reason: str):
        """Delete an event from Google Calendar."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete: {title}")
            logger.info(f"          Reason: {reason}")
            self.stats["deleted"] += 1
            return

        if self.google.delete_event(google_id, title):
            logger.info(f"Deleted: {title} - {reason}")
            self.stats["deleted"] += 1
        else:
            self.stats["errors"] += 1

    def _print_summary(self):
        """Print synchronization summary."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("SYNCHRONIZATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Outlook events fetched: {self.stats['outlook_events']}")
        logger.info(f"Passed AI filter:       {self.stats['filtered_in']}")
        logger.info(f"Skipped by AI filter:   {self.stats['filtered_out']}")
        logger.info("-" * 40)
        logger.info(f"Created:                {self.stats['created']}")
        logger.info(f"Updated:                {self.stats['updated']}")
        logger.info(f"Deleted:                {self.stats['deleted']}")
        logger.info(f"Errors:                 {self.stats['errors']}")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync Outlook calendar to Google Calendar with AI filtering"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without making changes",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the AI decision cache before syncing",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force sync regardless of working hours",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check if we should run (working hours only, unless forced)
    if not args.force and not is_working_hours():
        sys.exit(0)

    # Validate configuration
    missing = []
    if not config.OUTLOOK_ICS_URL:
        missing.append("OUTLOOK_ICS_URL")
    if not config.NEAR_AI_API_KEY:
        missing.append("NEAR_AI_API_KEY")

    if missing:
        logger.error(f"Missing required configuration: {', '.join(missing)}")
        logger.error("Please check your .env file or environment variables.")
        sys.exit(1)

    # Clear cache if requested
    if args.clear_cache:
        ai_filter = AIFilter()
        ai_filter.clear_cache()
        logger.info("AI decision cache cleared")

    # Run sync
    dry_run = args.dry_run or config.DRY_RUN
    sync = CalendarSync(dry_run=dry_run)

    success = sync.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
