"""Tests for OutlookClient ICS feed access."""

import unittest
from unittest import mock

import outlook_client


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
