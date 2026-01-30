#!/bin/bash
set -e

echo "Starting calendar sync service..."
echo "Schedule: Hourly between 07:00-14:00 on weekdays (Mon-Fri)"
echo "Excluding Norwegian public holidays"

# Create cron job - runs every hour from 07:00-14:00 on weekdays (Mon-Fri)
# Format: minute hour day month weekday command
# 0 7-14 * * 1-5 means: at minute 0 of hours 7,8,9,10,11,12,13,14 on Mon-Fri
echo "0 7-14 * * 1-5 cd /app && /opt/venv/bin/python sync_calendar.py >> /var/log/sync.log 2>&1" > /etc/cron.d/calendar-sync
chmod 0644 /etc/cron.d/calendar-sync
crontab /etc/cron.d/calendar-sync

# Run initial sync (forced, ignores working hours check)
echo "Running initial sync (forced)..."
cd /app && /opt/venv/bin/python sync_calendar.py --force

# Start cron in foreground
echo "Starting cron scheduler..."
cron -f
