import io
import json
import unittest
import urllib.error
from unittest.mock import patch
from fastapi import HTTPException
from app.auth import verify_admin_token


class PlatformAuthTests(unittest.TestCase):
    def test_platform_admin_and_teacher_can_use_shared_login(self):
        for role in ("admin", "teacher"):
            data = {"id": 1, "email": "admin", "role": role, "account_type": "staff"}
            with patch("app.auth.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(data).encode())) as remote:
                session = verify_admin_token(authorization="Bearer platform:test-jwt", token=None)
            self.assertEqual(session["role"], role)
            request = remote.call_args.args[0]
            self.assertEqual(request.full_url, "https://sdgs-action-platform.vercel.app/api/auth/me")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-jwt")

    def test_students_and_removed_accounts_are_rejected(self):
        with patch("app.auth.urllib.request.urlopen", return_value=io.BytesIO(b'{"role":"student","account_type":"student"}')):
            with self.assertRaises(HTTPException) as error:
                verify_admin_token(authorization="Bearer platform:student", token=None)
            self.assertEqual(error.exception.status_code, 403)
        expired = urllib.error.HTTPError("https://example.invalid", 401, "expired", {}, None)
        with patch("app.auth.urllib.request.urlopen", side_effect=expired):
            with self.assertRaises(HTTPException) as error:
                verify_admin_token(authorization="Bearer platform:expired", token=None)
            self.assertEqual(error.exception.status_code, 401)

    def test_auth_service_outage_does_not_grant_access(self):
        with patch("app.auth.urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            with self.assertRaises(HTTPException) as error:
                verify_admin_token(authorization="Bearer platform:test", token=None)
            self.assertEqual(error.exception.status_code, 503)
