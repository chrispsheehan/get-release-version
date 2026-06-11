#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from get_next_version import classify_bump, parse_prefixes, parse_release_bumps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run functional checks for commit-prefix versioning behavior."
    )
    parser.add_argument(
        "--major-prefixes",
        default="",
        help="Comma-separated commit prefixes that trigger a major bump.",
    )
    parser.add_argument(
        "--minor-prefixes",
        default="feat",
        help="Comma-separated commit prefixes that trigger a minor bump.",
    )
    parser.add_argument(
        "--patch-prefixes",
        default="fix",
        help="Comma-separated commit prefixes that trigger a patch bump.",
    )
    parser.add_argument(
        "--release-bumps",
        default="major,minor,patch",
        help="Comma-separated bump levels that should create a full release.",
    )
    parser.add_argument(
        "--direct-subject",
        default="fix: things",
        help="Example direct-push commit subject to validate.",
    )
    parser.add_argument(
        "--pr-subject",
        default="feat: this and that",
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


def run_command(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    command_env = os.environ.copy()
    if env:
        command_env.update(env)
    return subprocess.check_output(args, cwd=cwd, env=command_env, text=True).strip()


def create_repo_with_tag(tag: str | None) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmp = tempfile.TemporaryDirectory()
    repo = Path(tmp.name) / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)
    run_command(["git", "config", "user.name", "Functional Test"], cwd=repo)
    run_command(["git", "config", "user.email", "functional@example.invalid"], cwd=repo)
    (repo / "file.txt").write_text("test\n", encoding="utf-8")
    run_command(["git", "add", "file.txt"], cwd=repo)
    run_command(["git", "-c", "commit.gpgsign=false", "commit", "-m", "docs: initial"], cwd=repo)
    if tag:
        run_command(["git", "tag", tag], cwd=repo)
    return tmp, repo


def run_action_entrypoint(repo: Path, *args: str) -> dict[str, str]:
    git_config_global = tempfile.NamedTemporaryFile(delete=False)
    git_config_global.close()
    try:
        output = run_command(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "get_next_version.py"), *args],
            cwd=repo,
            env={
                "GITHUB_WORKSPACE": str(repo),
                "GIT_CONFIG_GLOBAL": git_config_global.name,
            },
        )
    finally:
        Path(git_config_global.name).unlink(missing_ok=True)
    payload = json.loads(output)
    assert isinstance(payload, dict)
    return {str(key): str(value) for key, value in payload.items()}


def format_bool(value: bool) -> str:
    return "yes" if value else "no"


def format_list(values: object) -> str:
    assert isinstance(values, list)
    return ", ".join(values) if values else "(none)"


def format_message(message: object) -> str:
    lines = [line.strip() for line in str(message).splitlines() if line.strip()]
    return " | ".join(lines)


def format_subject(check: dict[str, object]) -> str:
    subjects = check.get("subjects")
    if isinstance(subjects, list):
        return " | ".join(format_message(subject) for subject in subjects)
    return format_message(check["subject"])


def print_report(payload: dict[str, object]) -> None:
    checks = payload["checks"]
    assert isinstance(checks, list)

    print("Functional versioning tests")
    print()
    print("Configuration:")
    print(f"  major prefixes: {format_list(payload['major_prefixes'])}")
    print(f"  minor prefixes: {format_list(payload['minor_prefixes'])}")
    print(f"  patch prefixes: {format_list(payload['patch_prefixes'])}")
    print(f"  release bumps:   {format_list(payload['release_bumps'])}")
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


def assert_payload(name: str, actual: dict[str, str], expected: dict[str, str]) -> dict[str, object]:
    failures = [
        f"{key}: expected {expected_value!r}, got {actual.get(key)!r}"
        for key, expected_value in expected.items()
        if actual.get(key) != expected_value
    ]
    return {
        "name": name,
        "actual": actual,
        "expected": expected,
        "passes": not failures,
        "failures": failures,
    }


def run_output_checks() -> list[dict[str, object]]:
    scenarios = [
        (
            "patch_from_existing_tag",
            "1.2.3",
            ["--subjects", "fix: exercise patch tag output"],
            {
                "currentVersion": "1.2.3",
                "version": "1.2.4",
                "createNewTag": "true",
                "createNewRelease": "true",
                "majorAlias": "",
                "createMajorAlias": "false",
                "bump": "patch",
            },
        ),
        (
            "short_tag_normalization",
            "1.1",
            ["--subjects", "fix: exercise short tag output"],
            {
                "currentVersion": "1.1",
                "version": "1.1.1",
                "createNewTag": "true",
                "createNewRelease": "true",
                "majorAlias": "",
                "createMajorAlias": "false",
                "bump": "patch",
            },
        ),
        (
            "ignore_non_semver_tag",
            "prod",
            ["--subjects", "fix: exercise string tag ignore"],
            {
                "currentVersion": "0.0.1",
                "version": "0.0.2",
                "createNewTag": "true",
                "createNewRelease": "true",
                "majorAlias": "",
                "createMajorAlias": "false",
                "bump": "patch",
            },
        ),
        (
            "v1_major_alias",
            "v0.0.1",
            ["--subjects", "feat!: publish v1 action release", "--tag-prefix", "v", "--major-alias", "true"],
            {
                "currentVersion": "v0.0.1",
                "version": "v1.0.0",
                "createNewTag": "true",
                "createNewRelease": "true",
                "majorAlias": "v1",
                "createMajorAlias": "true",
                "bump": "major",
            },
        ),
        (
            "v2_major_alias",
            "v1.0.0",
            ["--subjects", "feat!: publish v2 action release", "--tag-prefix", "v", "--major-alias", "true"],
            {
                "currentVersion": "v1.0.0",
                "version": "v2.0.0",
                "createNewTag": "true",
                "createNewRelease": "true",
                "majorAlias": "v2",
                "createMajorAlias": "true",
                "bump": "major",
            },
        ),
        (
            "major_alias_default_disabled",
            "v0.0.1",
            ["--subjects", "feat!: publish v1 action release", "--tag-prefix", "v"],
            {
                "currentVersion": "v0.0.1",
                "version": "v1.0.0",
                "createNewTag": "true",
                "createNewRelease": "true",
                "majorAlias": "",
                "createMajorAlias": "false",
                "bump": "major",
            },
        ),
    ]

    results = []
    for name, tag, action_args, expected in scenarios:
        tmp, repo = create_repo_with_tag(tag)
        try:
            results.append(assert_payload(name, run_action_entrypoint(repo, *action_args), expected))
        finally:
            tmp.cleanup()
    return results


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
            "expected_bump": "minor",
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
            "name": "breaking_change_footer",
            "subject": "chore: update config\n\nBREAKING CHANGE: config format changed",
            "expected_create_tag": True,
            "expected_bump": "major",
            "actual_bump": bump_for(
                "chore: update config\n\nBREAKING CHANGE: config format changed",
                major=major,
                minor=minor,
                patch=patch,
            ),
        },
        {
            "name": "unmatched_subject",
            "subject": "docs: update readme",
            "expected_create_tag": False,
            "actual_bump": bump_for("docs: update readme", major=major, minor=minor, patch=patch),
        },
        {
            "name": "case_insensitive_prefix",
            "subject": "Fix: preserve compatibility",
            "expected_create_tag": True,
            "expected_bump": "patch",
            "actual_bump": bump_for("Fix: preserve compatibility", major=major, minor=minor, patch=patch),
        },
        {
            "name": "scoped_feat",
            "subject": "feat(api): add billing endpoint",
            "expected_create_tag": True,
            "expected_bump": "minor",
            "actual_bump": bump_for("feat(api): add billing endpoint", major=major, minor=minor, patch=patch),
        },
        {
            "name": "scoped_fix",
            "subject": "fix(parser): preserve whitespace",
            "expected_create_tag": True,
            "expected_bump": "patch",
            "actual_bump": bump_for("fix(parser): preserve whitespace", major=major, minor=minor, patch=patch),
        },
        {
            "name": "multi_commit_highest_bump_wins",
            "subjects": ["docs: tidy", "feat: add billing", "fix: patch worker"],
            "expected_create_tag": True,
            "expected_bump": "minor",
            "actual_bump": bump_for_subjects(
                ["docs: tidy", "feat: add billing", "fix: patch worker"],
                major=major,
                minor=minor,
                patch=patch,
            ),
        },
        {
            "name": "multi_commit_major_overrides_minor_patch",
            "subjects": ["fix: patch worker", "feat: add billing", "chore!: remove legacy api"],
            "expected_create_tag": True,
            "expected_bump": "major",
            "actual_bump": bump_for_subjects(
                ["fix: patch worker", "feat: add billing", "chore!: remove legacy api"],
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

    output_checks = run_output_checks()
    print()
    print("Output checks:")
    for check in output_checks:
        status = "PASS" if check["passes"] else "FAIL"
        print(f"  [{status}] {check['name']}")
        for failure in check["failures"]:
            print(f"        {failure}")

    all_output_checks_passed = all(check["passes"] for check in output_checks)
    print()
    print(f"Output summary: {sum(1 for check in output_checks if check['passes'])}/{len(output_checks)} checks passed")

    return 0 if payload["all_passed"] and all_output_checks_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
