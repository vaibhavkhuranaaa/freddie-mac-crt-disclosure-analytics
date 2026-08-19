from __future__ import annotations

import unittest
from unittest.mock import patch

from api.release import release_payload


class ReleaseContractTests(unittest.TestCase):
    def test_reports_deployed_git_revision(self) -> None:
        revision = "a" * 40
        with patch.dict("os.environ", {"VERCEL_GIT_COMMIT_SHA": revision}):
            self.assertEqual(
                release_payload(), {"status": "live", "source_sha": revision}
            )


if __name__ == "__main__":
    unittest.main()
