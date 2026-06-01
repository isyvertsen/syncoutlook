#!/usr/bin/env python3
"""Python-based scheduler for calendar sync - replaces system cron."""

import os
import subprocess
import sys
import time
import logging
from datetime import datetime

import schedule

import health_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8080"))


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
        health_server.record_sync(
            success=result.returncode == 0,
            returncode=result.returncode,
            ran_at=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to run sync: {e}")
        health_server.record_sync(
            success=False, returncode=-1, ran_at=datetime.now().isoformat()
        )


def main():
    print("Starting calendar sync scheduler...")
    print("Schedule: Every 30 min between 07:00-14:30 on weekdays (Mon-Fri)")
    print("Excluding Norwegian public holidays")
    print()

    # Start health endpoint so orchestrators can verify liveness.
    health_server.start_health_server(HEALTH_PORT)

    # Run initial sync (forced)
    print("Running initial sync...")
    initial = subprocess.run([sys.executable, "sync_calendar.py", "--force"])
    health_server.record_sync(
        success=initial.returncode == 0,
        returncode=initial.returncode,
        ran_at=datetime.now().isoformat(),
    )

    # Schedule runs every 30 minutes within the working-hours slot.
    # is_working_hours() gates actual syncs to 07:00-15:00, so the last
    # effective run is 14:30 (15:00 would be skipped).
    for hour in range(7, 15):
        for minute in ("00", "30"):
            schedule.every().day.at(f"{hour:02d}:{minute}").do(run_sync)
            logger.info(f"Scheduled sync at {hour:02d}:{minute}")

    print()
    print("Scheduler running. Press Ctrl+C to stop.")

    # Run scheduler loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()
