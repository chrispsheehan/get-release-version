# Get Release Version

This GitHub Action computes the next semver tag from commit subject prefixes since the latest matching semver tag.

---

## Features

- Runs through the Docker image defined in this directory's `Dockerfile`
- Resolves the checkout from `GITHUB_WORKSPACE` inside GitHub Actions
- Uses `GITHUB_WORKSPACE` from the local just harness for local runs
- Supports reading commit subjects from git history or from explicit `subjects`
- Follows [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) by default
- Supports custom major, minor, patch, release, and tag-prefix rules
- Accepts short manual tags like `1`, `1.1`, `v1`, and `v1.1` and normalizes them when calculating the next full semver tag
- Ignores non-version tags like `prod`, `dev`, or `latest`

Use this action from another repository with the moving major-version ref:

```yaml
- uses: chrispsheehan/get-release-version@v1
```

Default versioning contract:

- major: commits with `!`, `BREAKING CHANGE:`, or `BREAKING-CHANGE:`
- minor: commits with type `feat`
- patch: commits with type `fix`
- `release_bumps`: `major,minor,patch`
- `tag_prefix`: empty string
- when no matching semver tag exists, `currentVersion` falls back to `0.0.1` with the configured prefix

---

## Inputs

| Name             | Description                                                                     | Required | Default               |
|------------------|---------------------------------------------------------------------------------|----------|-----------------------|
| `subjects`       | Optional newline-delimited commit subjects to classify instead of git history   | ❌        | `""`                  |
| `major_prefixes` | Comma-separated commit subject prefixes that trigger a major bump               | ❌        | `""`                  |
| `minor_prefixes` | Comma-separated commit subject prefixes that trigger a minor bump               | ❌        | `feat`                |
| `patch_prefixes` | Comma-separated commit subject prefixes that trigger a patch bump               | ❌        | `fix`                 |
| `release_bumps`  | Comma-separated bump levels that create a full release                          | ❌        | `major,minor,patch`   |
| `tag_prefix`     | Optional prefix for semver tags, for example `v` for tags like `v1.2.3`         | ❌        | `""`                  |

Optional override behavior:

- `subjects` is useful in PR validation when previewing the version implied by the PR title rather than the branch commit list.
- `major_prefixes`, `minor_prefixes`, and `patch_prefixes` classify commit types differently from the defaults.
- `release_bumps` limits which bump levels create full release work while still allowing other matching subjects to create tags.
- `tag_prefix` discovers matching prefixed tags and emits versions with the same prefix.

---

## Outputs

| Name               | Description                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `currentVersion`   | Latest matching semver tag, or `0.0.1` with the configured prefix if none exists |
| `version`          | Next semver tag when a matching commit exists, otherwise the current tag     |
| `createNewTag`     | Whether a new semver tag should be created                                  |
| `createNewRelease` | Whether the resolved bump level should create full release work             |
| `bump`             | Resolved bump level, or empty when no matching commit exists                |

`createNewTag` decides whether the workflow should create a semver tag.
`createNewRelease` decides whether the workflow should run full release work for the resolved bump level.

---

## Example Usage

### Default release calculation

```yaml
jobs:
  version:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.get-release-version.outputs.version }}
      createNewTag: ${{ steps.get-release-version.outputs.createNewTag }}

    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Get next version
        id: get-release-version
        uses: chrispsheehan/get-release-version@v1
```

Use `fetch-depth: 0` when the action should calculate from repository tags and commit history.

### PR title preview

```yaml
jobs:
  preview:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Preview version from PR title
        id: get-release-version
        uses: chrispsheehan/get-release-version@v1
        with:
          subjects: ${{ github.event.pull_request.title }}

      - name: Show preview
        run: |
          echo "version=${{ steps.get-release-version.outputs.version }}"
          echo "createNewTag=${{ steps.get-release-version.outputs.createNewTag }}"
          echo "createNewRelease=${{ steps.get-release-version.outputs.createNewRelease }}"
```

Example JSON output:

```json
{"currentVersion":"0.14.0","version":"0.14.1","createNewTag":"true","createNewRelease":"true","bump":"patch"}
```

---

## Local Usage

Run the action entrypoint directly:

```sh
just local-test
```

---

## Tests

Run functional tests:

```sh
just functional-test
```

The functional tests cover:

- direct pushes with patch, minor, and breaking-change indicators
- squash/rebase PR subjects
- default merge-commit subjects that should not match
- case-insensitive prefix matching
- scoped commit types
- `!` and `BREAKING CHANGE:` breaking-change markers
- mixed commit lists where the highest bump level should win

Run unit tests locally:

```sh
just unit-test
```

---

## Publishing

The `push-on-main` workflow runs tests, calculates the next release tag with `tag_prefix: v`, publishes that tag, and force-updates the `v1` tag to the same commit. Keeping `v1` current lets users pin the action as:

```yaml
uses: chrispsheehan/get-release-version@v1
```
