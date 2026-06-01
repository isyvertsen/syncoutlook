"""Tests for the health-check HTTP server."""

import json
import unittest
import urllib.request
import urllib.error

import health_server


class HealthServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Port 0 lets the OS pick a free port; the server reports the bound one.
        cls.server = health_server.start_health_server(port=0)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_health_returns_200_with_status(self):
        with urllib.request.urlopen(f"{self.base}/health", timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            body = json.loads(resp.read())
        self.assertEqual(body["status"], "ok")
        self.assertIn("last_sync", body)

    def test_health_reflects_recorded_sync_state(self):
        health_server.record_sync(success=True, returncode=0, ran_at="2026-06-01T07:00:00")

        with urllib.request.urlopen(f"{self.base}/health", timeout=5) as resp:
            body = json.loads(resp.read())

        self.assertTrue(body["last_sync"]["success"])
        self.assertEqual(body["last_sync"]["returncode"], 0)
        self.assertEqual(body["last_sync"]["ran_at"], "2026-06-01T07:00:00")

    def test_unknown_path_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(f"{self.base}/nope", timeout=5)
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
