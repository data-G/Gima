import json
import hashlib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from human_ai.config import Config
from human_ai.memory import MemoryStore
from human_ai.permissions import PermissionManager


class PermissionManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = Config(data_dir=Path(self.temp.name))
        self.memory = MemoryStore(self.config.resolved_data_dir)
        self.permissions = PermissionManager(self.config, self.memory)

    def tearDown(self):
        self.temp.cleanup()

    def test_grant_requires_known_scope_and_expires_within_cap(self):
        grant = self.permissions.grant(["camera", "tools"], 999)
        self.assertEqual(grant.scopes, ["camera", "tools"])
        remaining = datetime.fromisoformat(grant.expires_at) - datetime.now(timezone.utc).astimezone()
        self.assertLessEqual(remaining, timedelta(minutes=30))
        self.permissions.require("camera")

    def test_missing_scope_is_rejected(self):
        self.permissions.grant(["camera"], 5)
        with self.assertRaises(PermissionError):
            self.permissions.require("tools")

    def test_expired_grant_is_removed(self):
        self.permissions.path.parent.mkdir(parents=True, exist_ok=True)
        self.permissions.path.write_text(
            json.dumps(
                {
                    "scopes": ["camera"],
                    "created_at": "2020-01-01T00:00:00+00:00",
                    "expires_at": "2020-01-01T00:01:00+00:00",
                }
            ),
            encoding="utf-8",
        )
        self.assertIsNone(self.permissions.current())
        self.assertFalse(self.permissions.path.exists())

    def test_revoke_removes_session(self):
        self.permissions.grant(["web"], 5)
        self.permissions.revoke()
        self.assertIsNone(self.permissions.current())

    def test_parent_password_uses_hash(self):
        self.config.parent_approval.password_sha256 = hashlib.sha256(
            "correct".encode("utf-8")
        ).hexdigest()
        self.assertTrue(self.permissions.verify_parent_password("correct"))
        self.assertFalse(self.permissions.verify_parent_password("wrong"))


if __name__ == "__main__":
    unittest.main()
