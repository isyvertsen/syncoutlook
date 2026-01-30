#!/bin/bash
set -e

# Default sync interval (in minutes)
SYNC_INTERVAL=${SYNC_INTERVAL:-15}

echo "Starting calendar sync service..."
echo "Sync interval: every ${SYNC_INTERVAL} minutes"

# Create cron job
echo "*/${SYNC_INTERVAL} * * * * cd /app && /usr/local/bin/python sync_calendar.py >> /var/log/sync.log 2>&1" > /etc/cron.d/calendar-sync
chmod 0644 /etc/cron.d/calendar-sync
crontab /etc/cron.d/calendar-sync

# Run initial sync
echo "Running initial sync..."
cd /app && python sync_calendar.py

# Start cron in foreground
echo "Starting cron scheduler..."
cron -f
