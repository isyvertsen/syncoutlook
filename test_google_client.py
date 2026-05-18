"""Tests for GoogleCalendarClient service-account authentication."""

import unittest
from unittest import mock

import config
import google_client


class AuthenticateServiceAccountTests(unittest.TestCase):
    def setUp(self):
        self.client = google_client.GoogleCalendarClient()

    @mock.patch.object(
        config, "GOOGLE_SERVICE_ACCOUNT_JSON", None, create=True
    )
    @mock.patch.object(
        config, "GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json", create=True
    )
    @mock.patch("google_client.build")
    @mock.patch(
        "google.oauth2.service_account.Credentials.from_service_account_file"
    )
    @mock.patch("google_client.os.path.exists")
    def test_authenticate_uses_service_account_credentials(
        self, mock_exists, mock_from_file, mock_build
    ):
        mock_exists.side_effect = lambda p: p == "service_account.json"
        fake_creds = object()
        mock_from_file.return_value = fake_creds
        fake_service = object()
        mock_build.return_value = fake_service

        result = self.client.authenticate()

        self.assertTrue(result)
        mock_from_file.assert_called_once_with(
            "service_account.json", scopes=config.GOOGLE_SCOPES
        )
        mock_build.assert_called_once_with(
            "calendar", "v3", credentials=fake_creds
        )
        self.assertIs(self.client.service, fake_service)

    @mock.patch.object(
        config, "GOOGLE_SERVICE_ACCOUNT_JSON", None, create=True
    )
    @mock.patch.object(
        config, "GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json", create=True
    )
    @mock.patch("google_client.os.path.exists", return_value=False)
    def test_authenticate_returns_false_when_key_file_missing(self, mock_exists):
        result = self.client.authenticate()

        self.assertFalse(result)
        self.assertIsNone(self.client.service)

    @mock.patch.object(
        config, "GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json", create=True
    )
    @mock.patch.object(
        config,
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        '{"type": "service_account", "project_id": "p"}',
        create=True,
    )
    @mock.patch("google_client.build")
    @mock.patch(
        "google.oauth2.service_account.Credentials.from_service_account_info"
    )
    @mock.patch(
        "google.oauth2.service_account.Credentials.from_service_account_file"
    )
    def test_authenticate_prefers_env_json_over_file(
        self, mock_from_file, mock_from_info, mock_build
    ):
        fake_creds = object()
        mock_from_info.return_value = fake_creds
        fake_service = object()
        mock_build.return_value = fake_service

        result = self.client.authenticate()

        self.assertTrue(result)
        mock_from_info.assert_called_once_with(
            {"type": "service_account", "project_id": "p"},
            scopes=config.GOOGLE_SCOPES,
        )
        mock_from_file.assert_not_called()
        self.assertIs(self.client.service, fake_service)


    @mock.patch.object(
        config, "GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json", create=True
    )
    @mock.patch.object(
        config, "GOOGLE_SERVICE_ACCOUNT_JSON", "{not valid json", create=True
    )
    @mock.patch("google_client.build")
    @mock.patch(
        "google.oauth2.service_account.Credentials.from_service_account_info"
    )
    @mock.patch(
        "google.oauth2.service_account.Credentials.from_service_account_file"
    )
    @mock.patch("google_client.os.path.exists", return_value=True)
    def test_authenticate_falls_back_to_file_when_env_json_invalid(
        self, mock_exists, mock_from_file, mock_from_info, mock_build
    ):
        fake_creds = object()
        mock_from_file.return_value = fake_creds
        fake_service = object()
        mock_build.return_value = fake_service

        result = self.client.authenticate()

        self.assertTrue(result)
        mock_from_file.assert_called_once_with(
            "service_account.json", scopes=config.GOOGLE_SCOPES
        )
        mock_from_info.assert_not_called()
        self.assertIs(self.client.service, fake_service)


if __name__ == "__main__":
    unittest.main()
