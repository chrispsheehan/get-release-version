#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from get_next_version import classify_bump, parse_prefixes, parse_release_bumps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run functional checks for commit-prefix versioning behavior."
    )
    parser.add_argument(
        "--major-prefixes",
        default="breaking,feat,!feat",
        help="Comma-separated commit prefixes that trigger a major bump.",
    )
    parser.add_argument(
        "--minor-prefixes",
        default="minor,fix,patch",
        help="Comma-separated commit prefixes that trigger a minor bump.",
    )
    parser.add_argument(
        "--patch-prefixes",
        default="chore,docs",
        help="Comma-separated commit prefixes that trigger a patch bump.",
    )
    parser.add_argument(
        "--release-bumps",
        default="major,minor",
        help="Comma-separated bump levels that should create a full release.",
    )
    parser.add_argument(
        "--direct-subject",
        default="chore: things",
        help="Example direct-push commit subject to validate.",
    )
    parser.add_argument(
        "--pr-subject",
        default="fix: this and that",
        help="Example PR subject or squash/rebase commit subject to validate.",
    )
    parser.add_argument(
        "--merge-commit-subject",
        default="Merge pull request #123 from example/branch",
        help="Example default merge-commit subject to validate.",
    )
    return parser.parse_args()


def bump_for(subject: str, *, major: list[str], minor: list[str], patch: list[str]) -> str:
    return classify_bump([subject], major=major, minor=minor, patch=patch) or ""


def bump_for_subjects(subjects: list[str], *, major: list[str], minor: list[str], patch: list[str]) -> str:
    return classify_bump(subjects, major=major, minor=minor, patch=patch) or ""


def format_bool(value: bool) -> str:
    return "yes" if value else "no"


def format_subject(check: dict[str, object]) -> str:
    subjects = check.get("subjects")
    if isinstance(subjects, list):
        return " | ".join(str(subject) for subject in subjects)
    return str(check["subject"])


def print_report(payload: dict[str, object]) -> None:
    checks = payload["checks"]
    assert isinstance(checks, list)

    print("Functional versioning tests")
    print()
    print("Configuration:")
    print(f"  major prefixes: {', '.join(payload['major_prefixes'])}")
    print(f"  minor prefixes: {', '.join(payload['minor_prefixes'])}")
    print(f"  patch prefixes: {', '.join(payload['patch_prefixes'])}")
    print(f"  release bumps:   {', '.join(payload['release_bumps'])}")
    print()
    print("Checks:")

    for check in checks:
        assert isinstance(check, dict)
        status = "PASS" if check["passes"] else "FAIL"
        expected_bump = check.get("expected_bump") or ""
        actual_bump = check["actual_bump"] or ""
        print(f"  [{status}] {check['name']}")
        print(f"         subject: {format_subject(check)}")
        print(
            "        expected: "
            f"create tag={format_bool(bool(check['expected_create_tag']))}, "
            f"bump={expected_bump or '-'}"
        )
        print(
            "          actual: "
            f"create tag={format_bool(bool(check['actual_create_tag']))}, "
            f"bump={actual_bump or '-'}"
        )

    passed = sum(1 for check in checks if isinstance(check, dict) and check["passes"])
    print()
    print(f"Summary: {passed}/{len(checks)} checks passed")


def main() -> int:
    args = parse_args()
    major = parse_prefixes(args.major_prefixes)
    minor = parse_prefixes(args.minor_prefixes)
    patch = parse_prefixes(args.patch_prefixes)
    release_bumps = parse_release_bumps(args.release_bumps)

    checks = [
        {
            "name": "direct_push_main",
            "subject": args.direct_subject,
            "expected_create_tag": True,
            "expected_bump": "patch",
            "actual_bump": bump_for(args.direct_subject, major=major, minor=minor, patch=patch),
        },
        {
            "name": "pr_merge_squash_or_rebase",
            "subject": args.pr_subject,
            "expected_create_tag": True,
            "expected_bump": "minor",
            "actual_bump": bump_for(args.pr_subject, major=major, minor=minor, patch=patch),
        },
        {
            "name": "pr_merge_default_merge_commit",
            "subject": args.merge_commit_subject,
            "expected_create_tag": False,
            "actual_bump": bump_for(args.merge_commit_subject, major=major, minor=minor, patch=patch),
        },
        {
            "name": "minor_direct_push",
            "subject": "feat: add reports endpoint",
            "expected_create_tag": True,
            "expected_bump": "major",
            "actual_bump": bump_for("feat: add reports endpoint", major=major, minor=minor, patch=patch),
        },
        {
            "name": "major_direct_push",
            "subject": "major: remove legacy api",
            "expected_create_tag": False,
            "actual_bump": bump_for("major: remove legacy api", major=major, minor=minor, patch=patch),
        },
        {
            "name": "breaking_bang_minor_prefix",
            "subject": "feat!: remove legacy auth flow",
            "expected_create_tag": True,
            "expected_bump": "major",
            "actual_bump": bump_for("feat!: remove legacy auth flow", major=major, minor=minor, patch=patch),
        },
        {
            "name": "breaking_bang_patch_prefix",
            "subject": "fix!: remove deprecated response field",
            "expected_create_tag": True,
            "expected_bump": "major",
            "actual_bump": bump_for("fix!: remove deprecated response field", major=major, minor=minor, patch=patch),
        },
        {
            "name": "unmatched_subject",
            "subject": "docs: update readme",
            "expected_create_tag": True,
            "expected_bump": "patch",
            "actual_bump": bump_for("docs: update readme", major=major, minor=minor, patch=patch),
        },
        {
            "name": "case_insensitive_prefix",
            "subject": "Fix: preserve compatibility",
            "expected_create_tag": True,
            "expected_bump": "minor",
            "actual_bump": bump_for("Fix: preserve compatibility", major=major, minor=minor, patch=patch),
        },
        {
            "name": "multi_commit_highest_bump_wins",
            "subjects": ["chore: tidy", "feat: add billing", "fix: patch worker"],
            "expected_create_tag": True,
            "expected_bump": "major",
            "actual_bump": bump_for_subjects(
                ["chore: tidy", "feat: add billing", "fix: patch worker"],
                major=major,
                minor=minor,
                patch=patch,
            ),
        },
        {
            "name": "multi_commit_major_overrides_minor_patch",
            "subjects": ["fix: patch worker", "feat: add billing", "major: remove legacy api"],
            "expected_create_tag": True,
            "expected_bump": "major",
            "actual_bump": bump_for_subjects(
                ["fix: patch worker", "feat: add billing", "major: remove legacy api"],
                major=major,
                minor=minor,
                patch=patch,
            ),
        },
    ]

    for check in checks:
        check["actual_create_tag"] = bool(check["actual_bump"])
        expected_bump = check.get("expected_bump")
        bump_matches = expected_bump is None or check["actual_bump"] == expected_bump
        check["passes"] = check["actual_create_tag"] == check["expected_create_tag"] and bump_matches

    payload = {
        "major_prefixes": major,
        "minor_prefixes": minor,
        "patch_prefixes": patch,
        "release_bumps": release_bumps,
        "checks": checks,
        "all_passed": all(check["passes"] for check in checks),
    }

    print_report(payload)
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
