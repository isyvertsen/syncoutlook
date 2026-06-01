"""Tests for OutlookClient ICS feed access."""

import unittest
from datetime import datetime, timedelta
from unittest import mock

import outlook_client


def _ics_dt(dt: datetime) -> str:
    """Format a datetime as a UTC ICS timestamp (YYYYMMDDTHHMMSSZ)."""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _build_recurring_ics(base: datetime, cancelled: datetime, moved_from: datetime, moved_to: datetime) -> bytes:
    """Build an ICS feed with one weekly series that has a cancelled
    occurrence (EXDATE) and a moved occurrence (RECURRENCE-ID override),
    mirroring how Outlook's published feed represents these."""
    uid = "series-123@outlook.com"
    master = "\r\n".join([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        "SUMMARY:Weekly Sync",
        f"DTSTART:{_ics_dt(base)}",
        f"DTEND:{_ics_dt(base + timedelta(hours=1))}",
        "RRULE:FREQ=WEEKLY;COUNT=8",
        f"EXDATE:{_ics_dt(cancelled)}",
        "STATUS:CONFIRMED",
        "END:VEVENT",
    ])
    override = "\r\n".join([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        "SUMMARY:Weekly Sync (moved)",
        f"RECURRENCE-ID:{_ics_dt(moved_from)}",
        f"DTSTART:{_ics_dt(moved_to)}",
        f"DTEND:{_ics_dt(moved_to + timedelta(hours=1))}",
        "STATUS:CONFIRMED",
        "END:VEVENT",
    ])
    cal = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "METHOD:PUBLISH",
        "PRODID:-//Microsoft Corporation//Outlook//EN",
        master,
        override,
        "END:VCALENDAR",
        "",
    ])
    return cal.encode("utf-8")


class RecurringExceptionTests(unittest.TestCase):
    """A cancelled (EXDATE) or moved (RECURRENCE-ID) occurrence of a
    recurring series must not leave a ghost event behind."""

    def setUp(self):
        self.client = outlook_client.OutlookClient()
        self.client.ics_url = "https://example.com/calendar.ics"

        # Anchor the series two weeks in the past so all 8 weekly
        # occurrences fall inside a generous sync window.
        now = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        self.base = now - timedelta(days=14)
        self.cancelled = self.base + timedelta(days=21)      # week 3 -> EXDATE
        self.moved_from = self.base + timedelta(days=7)       # week 1 original
        self.moved_to = self.base + timedelta(days=7, hours=5)  # week 1 moved to 14:00

        ics = _build_recurring_ics(self.base, self.cancelled, self.moved_from, self.moved_to)
        self._patcher = mock.patch("outlook_client.requests.get")
        mock_get = self._patcher.start()
        mock_get.return_value = mock.Mock(content=ics, status_code=200, raise_for_status=mock.Mock())
        self.addCleanup(self._patcher.stop)

        self.events = self.client.get_calendar_events(days_back=30, days_ahead=90)

    def _dates(self):
        return {e["start"][:10] for e in self.events}

    def test_cancelled_occurrence_is_excluded(self):
        # The EXDATE'd week must not produce an event.
        self.assertNotIn(
            self.cancelled.date().isoformat(),
            self._dates(),
            "Cancelled occurrence (EXDATE) was still generated",
        )

    def test_moved_occurrence_has_no_ghost_at_original_time(self):
        # The original 09:00 slot of the moved week must be gone...
        week1 = [e for e in self.events if e["start"][:10] == self.moved_from.date().isoformat()]
        self.assertEqual(len(week1), 1, "Expected exactly one event on the moved week (no ghost)")
        # ...and the surviving event must be at the moved-to time (14:00).
        hour = datetime.fromisoformat(week1[0]["start"].replace("Z", "+00:00")).hour
        self.assertEqual(hour, self.moved_to.hour, "Moved occurrence not at its new time")

    def test_total_occurrence_count(self):
        # 8 weekly occurrences, minus 1 cancelled = 7 (one of which is the moved override).
        self.assertEqual(len(self.events), 7)


class AuthenticateTests(unittest.TestCase):
    def setUp(self):
        self.client = outlook_client.OutlookClient()
        self.client.ics_url = "https://example.com/calendar.ics"

    @mock.patch("outlook_client.requests.get")
    @mock.patch("outlook_client.requests.head")
    def test_authenticate_uses_get_not_head(self, mock_head, mock_get):
        # Outlook's ICS endpoint returns 405 for HEAD but 200 for GET.
        mock_get.return_value = mock.Mock(status_code=200)

        result = self.client.authenticate()

        self.assertTrue(result)
        mock_get.assert_called_once()
        mock_head.assert_not_called()

    @mock.patch("outlook_client.requests.get")
    def test_authenticate_returns_false_on_error_status(self, mock_get):
        mock_get.return_value = mock.Mock(status_code=405)

        result = self.client.authenticate()

        self.assertFalse(result)

    def test_authenticate_returns_false_when_url_missing(self):
        self.client.ics_url = None

        self.assertFalse(self.client.authenticate())


if __name__ == "__main__":
    unittest.main()
