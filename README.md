# get-release-version

Repo-local GitHub Action and CLI for computing the next semver tag from commit subject prefixes since the latest semver tag.

The GitHub Action itself runs through the Docker image defined in this directory's `Dockerfile`.
The `justfile` is only a local test harness; the Docker action itself runs the Python entrypoint directly.
Inside GitHub Actions, the script resolves the checkout from `GITHUB_WORKSPACE` rather than assuming a fixed Docker working directory.
For local runs, `just local-test` sets `GITHUB_WORKSPACE` to the repository root before invoking the script.

Default prefix contract:

- `major_prefixes`: `breaking,feat,!feat`
- `minor_prefixes`: `minor,fix,patch`
- `patch_prefixes`: `chore,docs`
- `release_bumps`: `major,minor`
- `tag_prefix`: empty string

Optional override:

- `subjects`: newline-delimited subjects to classify instead of reading git history
- this is useful in PR validation when you want to preview the version implied by the PR title rather than the branch commit list
- `release_bumps`: comma-delimited bump levels that should create a full release; for example `major` limits releases to major bumps while still allowing minor and patch subjects to create tags
- `tag_prefix`: optional tag prefix; for example `v` discovers tags like `v1.2.3` and outputs versions like `v1.2.4`

## Local Usage

Directly on your machine:

```sh
just local-test \
  --major-prefixes breaking,feat,!feat \
  --minor-prefixes minor,fix,patch \
  --patch-prefixes chore,docs \
  --tag-prefix v
```

Functional tests:

```sh
just functional-test \
  --major-prefixes breaking,feat,!feat \
  --minor-prefixes minor,fix,patch \
  --patch-prefixes chore,docs
```

The functional tests cover:

- direct pushes with patch, minor, and major prefixes
- squash/rebase PR subjects
- default merge-commit subjects that should not match
- case-insensitive prefix matching
- mixed commit lists where the highest bump level should win

Workspace resolution unit test:

```sh
just unit-test
```

Example JSON output with `--tag-prefix v`:

```json
{"currentVersion":"v0.14.0","version":"v0.14.1","createNewTag":"true","createNewRelease":"false","bump":"patch"}
```

`createNewTag` decides whether the workflow should create a semver tag.
`createNewRelease` decides whether the workflow should run full release work for the resolved bump level.
