import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import tomlkit

from qobuz_login import extract_credentials, save_credentials


class QobuzLoginTests(unittest.TestCase):
    def test_successful_qobuz_response_with_query_is_accepted(self):
        result = extract_credentials(
            "https://www.qobuz.com/api.json/0.2/user/login?extra=partner", 200,
            {"user": {"id": 12345}, "user_auth_token": "dummy-test-token"},
        )
        self.assertEqual(result, ("12345", "dummy-test-token"))

    def test_unrelated_origin_and_failed_or_malformed_login_are_ignored(self):
        good = {"user": {"id": 12345}, "user_auth_token": "dummy-test-token"}
        for url in ("https://other.example/api.json/0.2/user/login",
                    "http://www.qobuz.com/api.json/0.2/user/login",
                    "https://www.qobuz.com/api.json/0.2/user/logout"):
            self.assertIsNone(extract_credentials(url, 200, good))
        url = "https://www.qobuz.com/api.json/0.2/user/login"
        self.assertIsNone(extract_credentials(url, 401, good))
        for payload in ({}, [], {"user": None}, {"user": {"id": True}, "user_auth_token": "dummy"},
                        {"user": {"id": "name@example.com"}, "user_auth_token": "dummy"}):
            self.assertIsNone(extract_credentials(url, 200, payload))

    def test_partner_response_filter_handles_form_and_json(self):
        url = "https://www.qobuz.com/api.json/0.2/user/login"
        payload = {"user": {"id": 12345}, "user_auth_token": "dummy"}
        self.assertIsNone(extract_credentials(url, 200, payload, "email=test"))
        self.assertIsNotNone(extract_credentials(url, 200, payload, "extra=partner&email=test"))
        self.assertIsNotNone(extract_credentials(url, 200, payload, '{"extra":"partner"}'))

    def test_save_changes_only_auth_fields_and_never_prints_token(self):
        with tempfile.TemporaryDirectory(dir=".runtime") as directory:
            config = Path(directory) / "streamrip.toml"
            config.write_text('# Keep this comment\n[qobuz]\nquality = 4\napp_id = "existing"\n'
                              '[downloads]\nfolder = "my-music"\n[tidal]\naccess_token = "dummy-tidal"\n')
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                save_credentials(config, "12345", "dummy-qobuz-token")
            data = tomlkit.parse(config.read_text())
            self.assertTrue(data["qobuz"]["use_auth_token"])
            self.assertEqual(data["qobuz"]["email_or_userid"], "12345")
            self.assertEqual(data["qobuz"]["password_or_token"], "dummy-qobuz-token")
            self.assertEqual(data["qobuz"]["quality"], 4)
            self.assertEqual(data["qobuz"]["app_id"], "existing")
            self.assertEqual(data["downloads"]["folder"], "my-music")
            self.assertEqual(data["tidal"]["access_token"], "dummy-tidal")
            self.assertIn("# Keep this comment", config.read_text())
            self.assertEqual(output.getvalue(), "")
            self.assertEqual(list((Path(directory) / ".runtime/qobuz").iterdir()), [])

    def test_failed_atomic_replace_preserves_original_and_removes_temporary_token(self):
        with tempfile.TemporaryDirectory(dir=".runtime") as directory:
            config = Path(directory) / "streamrip.toml"
            original = '[qobuz]\nquality = 3\n'
            config.write_text(original)
            with patch("qobuz_login.os.replace", side_effect=OSError("simulated failure")):
                with self.assertRaises(OSError):
                    save_credentials(config, "12345", "dummy-qobuz-token")
            self.assertEqual(config.read_text(), original)
            self.assertEqual(list((Path(directory) / ".runtime/qobuz").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
