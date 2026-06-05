#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


@dataclass(frozen=True, order=True)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "SemVer | None":
        match = SEMVER_RE.fullmatch(value.strip())
        if not match:
            return None
        major, minor, patch = (int(part) for part in match.groups())
        return cls(major, minor, patch)

    def bump(self, level: str) -> "SemVer":
        if level == "major":
            return SemVer(self.major + 1, 0, 0)
        if level == "minor":
            return SemVer(self.major, self.minor + 1, 0)
        if level == "patch":
            return SemVer(self.major, self.minor, self.patch + 1)
        raise ValueError(f"Unknown bump level: {level}")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, cwd=resolve_workspace()).strip()


def resolve_workspace() -> Path:
    workspace = os.environ.get("GITHUB_WORKSPACE")
    if not workspace:
        raise RuntimeError("GITHUB_WORKSPACE is not set")
    return Path(workspace)


def ensure_safe_directory() -> None:
    workspace = resolve_workspace()
    subprocess.run(
        ["git", "config", "--global", "--add", "safe.directory", str(workspace)],
        check=True,
        text=True,
        capture_output=True,
    )


def parse_prefixes(raw: str) -> list[str]:
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def parse_release_bumps(raw: str) -> list[str]:
    allowed = {"major", "minor", "patch"}
    bumps = parse_prefixes(raw)
    invalid = [item for item in bumps if item not in allowed]
    if invalid:
        raise ValueError(f"Unknown release bump level(s): {', '.join(invalid)}")
    return bumps


def latest_semver_tag() -> str:
    tags = git("tag", "--merged", "HEAD", "--sort=-v:refname").splitlines()
    for tag in tags:
        if SEMVER_RE.fullmatch(tag):
            return tag
    return "0.0.0"


def commit_subjects_since(tag: str) -> list[str]:
    if tag == "0.0.0" and not has_real_tag(tag):
        output = git("log", "--pretty=format:%s")
    else:
        output = git("log", f"{tag}..HEAD", "--pretty=format:%s")
    return [line.strip() for line in output.splitlines() if line.strip()]


def has_real_tag(tag: str) -> bool:
    try:
        subprocess.check_output(
            ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
            text=True,
            cwd=resolve_workspace(),
        )
    except subprocess.CalledProcessError:
        return False
    return True


def classify_bump(subjects: list[str], *, major: list[str], minor: list[str], patch: list[str]) -> str | None:
    bump = None
    for subject in subjects:
        lowered = subject.lower()
        prefix_segment = lowered.split(":", 1)[0]
        if prefix_segment.endswith("!"):
            return "major"
        if any(lowered.startswith(f"{prefix}:") for prefix in major):
            return "major"
        if any(lowered.startswith(f"{prefix}:") for prefix in minor):
            bump = "minor" if bump != "minor" else bump
            continue
        if any(lowered.startswith(f"{prefix}:") for prefix in patch):
            if bump is None:
                bump = "patch"
    return bump


def write_output(name: str, value: str) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        raise RuntimeError("GITHUB_OUTPUT is not set")
    with Path(github_output).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute the next semver version from commit subject prefixes since the latest semver tag."
    )
    parser.add_argument(
        "--subjects",
        default=os.environ.get("SUBJECTS", ""),
        help="Optional newline-delimited commit subjects to classify instead of reading git history.",
    )
    parser.add_argument(
        "--major-prefixes",
        default=os.environ.get("MAJOR_PREFIXES", "breaking,feat,!feat"),
        help="Comma-separated commit prefixes that trigger a major bump.",
    )
    parser.add_argument(
        "--minor-prefixes",
        default=os.environ.get("MINOR_PREFIXES", "minor,fix,patch"),
        help="Comma-separated commit prefixes that trigger a minor bump.",
    )
    parser.add_argument(
        "--patch-prefixes",
        default=os.environ.get("PATCH_PREFIXES", "chore,docs"),
        help="Comma-separated commit prefixes that trigger a patch bump.",
    )
    parser.add_argument(
        "--release-bumps",
        default=os.environ.get("RELEASE_BUMPS", "major,minor"),
        help="Comma-separated bump levels that should create a full release.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format when running outside GitHub Actions.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = resolve_workspace()
    if not (workspace / ".git").exists():
        raise RuntimeError(f"Not a git repository: {workspace}")
    ensure_safe_directory()
    current_tag = latest_semver_tag()
    current_version = SemVer.parse(current_tag) or SemVer(0, 0, 0)
    subjects = [line.strip() for line in args.subjects.splitlines() if line.strip()]
    if not subjects:
        subjects = commit_subjects_since(current_tag)

    bump = classify_bump(
        subjects,
        major=parse_prefixes(args.major_prefixes),
        minor=parse_prefixes(args.minor_prefixes),
        patch=parse_prefixes(args.patch_prefixes),
    )

    next_version = str(current_version.bump(bump)) if bump else str(current_version)
    release_bumps = set(parse_release_bumps(args.release_bumps))
    payload = {
        "currentVersion": str(current_version),
        "version": next_version,
        "createNewTag": "true" if bump else "false",
        "createNewRelease": "true" if bump in release_bumps else "false",
        "bump": bump or "",
    }

    if os.environ.get("GITHUB_OUTPUT"):
        for key, value in payload.items():
            write_output(key, value)
        return 0

    if args.format == "text":
        print(next_version)
    else:
        print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
