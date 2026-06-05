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
    def test_resolve_workspace_walks_up_to_git_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            nested = repo / ".github" / "actions" / "get-next-version"
            nested.mkdir(parents=True)
            (repo / ".git").mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(nested)
                self.assertEqual(resolve_workspace().resolve(), repo.resolve())
            finally:
                os.chdir(old_cwd)

    def test_resolve_workspace_prefers_github_workspace(self) -> None:
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


class ReleaseBumpTests(unittest.TestCase):
    def test_parse_release_bumps_accepts_configured_levels(self) -> None:
        self.assertEqual(parse_release_bumps("major,minor"), ["major", "minor"])
        self.assertEqual(parse_release_bumps(" major , patch "), ["major", "patch"])

    def test_parse_release_bumps_rejects_unknown_levels(self) -> None:
        with self.assertRaises(ValueError):
            parse_release_bumps("major,tiny")


if __name__ == "__main__":
    unittest.main()
