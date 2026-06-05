#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from get_next_version import parse_release_bumps, resolve_workspace


class WorkspaceResolutionTests(unittest.TestCase):
    def test_resolve_workspace_uses_github_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            old_value = os.environ.get("GITHUB_WORKSPACE")
            try:
                os.environ["GITHUB_WORKSPACE"] = str(repo)
                self.assertEqual(resolve_workspace().resolve(), repo.resolve())
            finally:
                if old_value is None:
                    os.environ.pop("GITHUB_WORKSPACE", None)
                else:
                    os.environ["GITHUB_WORKSPACE"] = old_value

    def test_resolve_workspace_requires_github_workspace(self) -> None:
        old_value = os.environ.get("GITHUB_WORKSPACE")
        try:
            os.environ.pop("GITHUB_WORKSPACE", None)
            with self.assertRaisesRegex(RuntimeError, "GITHUB_WORKSPACE is not set"):
                resolve_workspace()
        finally:
            if old_value is None:
                os.environ.pop("GITHUB_WORKSPACE", None)
            else:
                os.environ["GITHUB_WORKSPACE"] = old_value


class ReleaseBumpTests(unittest.TestCase):
    def test_parse_release_bumps_accepts_configured_levels(self) -> None:
        self.assertEqual(parse_release_bumps("major,minor"), ["major", "minor"])
        self.assertEqual(parse_release_bumps(" major , patch "), ["major", "patch"])

    def test_parse_release_bumps_rejects_unknown_levels(self) -> None:
        with self.assertRaises(ValueError):
            parse_release_bumps("major,tiny")


if __name__ == "__main__":
    unittest.main()
