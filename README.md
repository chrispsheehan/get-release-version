# Get Release Version

This GitHub Action computes the next semver tag from commit subject prefixes since the latest matching semver tag.

---

## Features

- Runs as a composite action with the runner's `python3` and `git`
- Resolves the checkout from `GITHUB_WORKSPACE` inside GitHub Actions and reads commit subjects from git history or from explicit `subjects`
- Follows [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) by default

---

## Usage

```yaml
jobs:
  version:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          # Required when reading tags and commit history.
          fetch-depth: 0

      - id: get-release-version
        uses: chrispsheehan/get-release-version@v1
        with:
          # PR title or newline-delimited commit subjects.
          # Default: git history
          subjects: ''

          # Custom commit types for major bumps. Breaking markers still apply.
          # Default: ''
          major_prefixes: ''

          # Default: feat
          minor_prefixes: feat

          # Default: fix
          patch_prefixes: fix

          # Bump levels that should publish a release.
          # Default: major,minor,patch
          release_bumps: major,minor,patch

          # Prefix for semver tags, for example v1.2.3.
          # Default: ''
          tag_prefix: ''

          # Populate majorAlias/createMajorAlias, for example v1.
          # Default: false
          major_alias: false

      - name: Show version
        run: |
          echo "version=${{ steps.get-release-version.outputs.version }}"
          echo "majorAlias=${{ steps.get-release-version.outputs.majorAlias }}"
          echo "createNewTag=${{ steps.get-release-version.outputs.createNewTag }}"
          echo "createNewRelease=${{ steps.get-release-version.outputs.createNewRelease }}"
          echo "createMajorAlias=${{ steps.get-release-version.outputs.createMajorAlias }}"
```

---

## Inputs

All inputs are optional.

| Name             | Description                                                                     | Default               |
|------------------|---------------------------------------------------------------------------------|-----------------------|
| `subjects`       | PR title or newline-delimited commit subjects to classify instead of git history. Useful for PR previews. | `""`                  |
| `major_prefixes` | Custom commit types that trigger a major bump. Breaking markers still apply.    | `""`                  |
| `minor_prefixes` | Commit types that trigger a minor bump.                                         | `feat`                |
| `patch_prefixes` | Commit types that trigger a patch bump.                                         | `fix`                 |
| `release_bumps`  | Bump levels that create a full release. Other matching bumps can still create tags. | `major,minor,patch`   |
| `tag_prefix`     | Semver tag prefix to discover and emit, for example `v` for `v1.2.3`.           | `""`                  |
| `major_alias`    | Whether to populate `majorAlias` and `createMajorAlias` for releases like `v1.0.0`. | `false`               |

---

## Outputs

| Name               | Description                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `currentVersion`   | Latest matching semver tag, or `0.0.1` with the configured prefix if none exists |
| `version`          | Next semver tag when a matching commit exists, otherwise the current tag     |
| `createNewTag`     | Whether the workflow should create a semver tag                             |
| `createNewRelease` | Whether the resolved bump should publish a release                          |
| `majorAlias`       | Moving major-version alias for the resolved version, for example `v1`       |
| `createMajorAlias` | Whether the workflow should create or update `majorAlias`                   |
| `bump`             | Resolved bump level, or empty when no matching commit exists                |

---

## Local Usage

Run the action entrypoint directly:

```sh
just local-test
```

Run functional tests locally:

```sh
just functional-test
```

Run unit tests locally:

```sh
just unit-test
```

---

## Publishing

For GitHub Actions, publish immutable semver tags like `v1.1.0` and keep a moving major alias like `v1` for consumers.

The `release` workflow calculates tags with `tag_prefix: v` and `major_alias: true`. That means a breaking change from `v0.0.1` produces `version=v1.0.0` and `majorAlias=v1`. The workflow publishes the GitHub Release for `version`, then creates or updates the Git tag named by `majorAlias`.

For application and library repositories, you usually do not need a moving `v1` alias. Prefer publishing only immutable semver tags and leave the major alias disabled:

```yaml
- name: Get next version
  id: get-release-version
  uses: chrispsheehan/get-release-version@v1
  with:
    tag_prefix: v
    major_alias: false
```

Then create GitHub Releases only for `version`, for example `v1.0.0`, `v1.0.1`, and `v1.1.0`.
