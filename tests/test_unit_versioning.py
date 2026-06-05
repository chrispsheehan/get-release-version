#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from get_next_version import (
    SemVer,
    classify_bump,
    format_tag,
    latest_semver_tag,
    parse_release_bumps,
    parse_tag_version,
    resolve_workspace,
)


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


class ClassifyBumpTests(unittest.TestCase):
    def test_classify_bump_supports_conventional_commit_scopes(self) -> None:
        self.assertEqual(
            classify_bump(["feat(api): add reports"], major=[], minor=["feat"], patch=["fix"]),
            "minor",
        )
        self.assertEqual(
            classify_bump(["fix(parser): preserve whitespace"], major=[], minor=["feat"], patch=["fix"]),
            "patch",
        )

    def test_classify_bump_supports_bang_breaking_change(self) -> None:
        self.assertEqual(
            classify_bump(["docs!: rewrite public api docs"], major=[], minor=["feat"], patch=["fix"]),
            "major",
        )

    def test_classify_bump_supports_breaking_change_footer(self) -> None:
        self.assertEqual(
            classify_bump(
                ["chore: update config\n\nBREAKING CHANGE: config file format changed"],
                major=[],
                minor=["feat"],
                patch=["fix"],
            ),
            "major",
        )


class TagPrefixTests(unittest.TestCase):
    def test_parse_tag_version_accepts_configured_prefix(self) -> None:
        self.assertEqual(parse_tag_version("v1.2.3", "v"), SemVer(1, 2, 3))
        self.assertEqual(parse_tag_version("v1.2", "v"), SemVer(1, 2, 0))
        self.assertEqual(parse_tag_version("v1", "v"), SemVer(1, 0, 0))

    def test_parse_tag_version_rejects_missing_configured_prefix(self) -> None:
        self.assertIsNone(parse_tag_version("1.2.3", "v"))
        self.assertIsNone(parse_tag_version("prod", "v"))

    def test_parse_tag_version_keeps_plain_semver_default(self) -> None:
        self.assertEqual(parse_tag_version("1.2.3", ""), SemVer(1, 2, 3))
        self.assertEqual(parse_tag_version("1.2", ""), SemVer(1, 2, 0))
        self.assertEqual(parse_tag_version("1", ""), SemVer(1, 0, 0))
        self.assertIsNone(parse_tag_version("v1.2.3", ""))
        self.assertIsNone(parse_tag_version("prod", ""))

    def test_format_tag_applies_configured_prefix(self) -> None:
        self.assertEqual(format_tag(SemVer(1, 2, 3), "v"), "v1.2.3")
        self.assertEqual(format_tag(SemVer(1, 2, 3), ""), "1.2.3")


class LatestSemverTagTests(unittest.TestCase):
    def test_latest_semver_tag_falls_back_to_initial_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "CI Test"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "ci@example.invalid"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            (repo / "file.txt").write_text("test\n", encoding="utf-8")
            subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "-c", "commit.gpgsign=false", "commit", "-m", "docs: initial"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

            old_value = os.environ.get("GITHUB_WORKSPACE")
            try:
                os.environ["GITHUB_WORKSPACE"] = str(repo)
                self.assertEqual(latest_semver_tag(""), "0.0.1")
                self.assertEqual(latest_semver_tag("v"), "v0.0.1")
            finally:
                if old_value is None:
                    os.environ.pop("GITHUB_WORKSPACE", None)
                else:
                    os.environ["GITHUB_WORKSPACE"] = old_value

    def test_latest_semver_tag_accepts_short_manual_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "CI Test"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "ci@example.invalid"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            (repo / "file.txt").write_text("test\n", encoding="utf-8")
            subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "-c", "commit.gpgsign=false", "commit", "-m", "docs: initial"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "tag", "v1.1"], cwd=repo, check=True, capture_output=True)

            old_value = os.environ.get("GITHUB_WORKSPACE")
            try:
                os.environ["GITHUB_WORKSPACE"] = str(repo)
                self.assertEqual(latest_semver_tag("v"), "v1.1")
            finally:
                if old_value is None:
                    os.environ.pop("GITHUB_WORKSPACE", None)
                else:
                    os.environ["GITHUB_WORKSPACE"] = old_value

    def test_latest_semver_tag_ignores_non_version_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "CI Test"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "ci@example.invalid"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            (repo / "file.txt").write_text("test\n", encoding="utf-8")
            subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "-c", "commit.gpgsign=false", "commit", "-m", "docs: initial"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "tag", "prod"], cwd=repo, check=True, capture_output=True)

            old_value = os.environ.get("GITHUB_WORKSPACE")
            try:
                os.environ["GITHUB_WORKSPACE"] = str(repo)
                self.assertEqual(latest_semver_tag(""), "0.0.1")
                self.assertEqual(latest_semver_tag("v"), "v0.0.1")
            finally:
                if old_value is None:
                    os.environ.pop("GITHUB_WORKSPACE", None)
                else:
                    os.environ["GITHUB_WORKSPACE"] = old_value


if __name__ == "__main__":
    unittest.main()
