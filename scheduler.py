#!/usr/bin/env python3
"""Python-based scheduler for calendar sync - replaces system cron."""

import subprocess
import sys
import time
import logging
from datetime import datetime

import schedule

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_sync():
    """Run the calendar sync script."""
    logger.info(f"Running scheduled sync at {datetime.now()}")
    try:
        result = subprocess.run(
            [sys.executable, "sync_calendar.py"],
            capture_output=False,
        )
        if result.returncode != 0:
            logger.warning(f"Sync exited with code {result.returncode}")
    except Exception as e:
        logger.error(f"Failed to run sync: {e}")


def main():
    print("Starting calendar sync scheduler...")
    print("Schedule: Hourly between 07:00-14:00 on weekdays (Mon-Fri)")
    print("Excluding Norwegian public holidays")
    print()

    # Run initial sync (forced)
    print("Running initial sync...")
    subprocess.run([sys.executable, "sync_calendar.py", "--force"])

    # Schedule hourly runs at minute 0 for hours 7-14
    for hour in range(7, 15):
        schedule.every().day.at(f"{hour:02d}:00").do(run_sync)
        logger.info(f"Scheduled sync at {hour:02d}:00")

    print()
    print("Scheduler running. Press Ctrl+C to stop.")

    # Run scheduler loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()
