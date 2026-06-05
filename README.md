# get-release-version

Repo-local GitHub Action and CLI for computing the next semver tag from commit subject prefixes since the latest semver tag.

The GitHub Action itself runs through the Docker image defined in this directory's `Dockerfile`.
The `justfile` is only a local test harness; the Docker action itself runs the Python entrypoint directly.
Inside GitHub Actions, the script resolves the checkout from `GITHUB_WORKSPACE` rather than assuming a fixed Docker working directory.
For local runs, `just local-test` sets `GITHUB_WORKSPACE` to the repository root before invoking the script.

By default, this action follows the [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) versioning rules.

Default versioning contract:

- major: commits with `!`, `BREAKING CHANGE:`, or `BREAKING-CHANGE:`
- minor: commits with type `feat`
- patch: commits with type `fix`
- `release_bumps`: `major,minor,patch`
- `tag_prefix`: empty string
- when no matching semver tag exists, `currentVersion` falls back to `0.0.1` with the configured prefix
- short manual tags like `1`, `1.1`, `v1`, and `v1.1` are accepted as previous versions and normalized when calculating the next full semver tag
- non-version tags like `prod`, `dev`, or `latest` are ignored for version calculation

## GitHub Actions Usage

```yaml
- uses: chrispsheehan/get-release-version@<version>
  id: get-release-version
```

## Inputs

| Name | Default | Description |
| --- | --- | --- |
| `subjects` | empty string | Optional newline-delimited commit subjects to classify instead of reading git history. Useful for PR title previews. |
| `major_prefixes` | empty string | Comma-delimited commit types that trigger a major bump. Conventional Commits breaking-change markers still trigger major bumps. |
| `minor_prefixes` | `feat` | Comma-delimited commit types that trigger a minor bump. |
| `patch_prefixes` | `fix` | Comma-delimited commit types that trigger a patch bump. |
| `release_bumps` | `major,minor,patch` | Comma-delimited bump levels that should create a full release. For example, `major` limits releases to major bumps while still allowing minor and patch commits to create tags. |
| `tag_prefix` | empty string | Optional prefix for semver tags. For example, `v` discovers tags like `v1`, `v1.2`, and `v1.2.3`, then outputs versions like `v1.2.4`. |

## Outputs

| Name | Description |
| --- | --- |
| `currentVersion` | Latest matching semver tag, or `0.0.1` with the configured prefix when none exists. |
| `version` | Next semver tag when a matching commit exists, otherwise the current tag. |
| `createNewTag` | Whether a new semver tag should be created. |
| `createNewRelease` | Whether the resolved bump level should create full release work. |
| `bump` | Resolved bump level: `major`, `minor`, `patch`, or empty when no matching commit exists. |

## Preview PR Version

You can pass a PR title through `subjects` to preview the version impact before merging:

```yaml
test-next-version-action:
  name: Next Version Action
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v6
      with:
        fetch-depth: 0

    - name: Execute get-release-version action
      id: get_next_version
      uses: chrispsheehan/get-release-version@<version>
      with:
        subjects: ${{ github.event.pull_request.title }}

    - name: Show action outputs
      run: |
        echo "currentVersion=${{ steps.get_next_version.outputs.currentVersion }}"
        echo "version=${{ steps.get_next_version.outputs.version }}"
        echo "createNewTag=${{ steps.get_next_version.outputs.createNewTag }}"
        echo "createNewRelease=${{ steps.get_next_version.outputs.createNewRelease }}"
        echo "bump=${{ steps.get_next_version.outputs.bump }}"
```

With the default Conventional Commits rules, a PR title like `feat: add reports` previews a minor bump, `fix: preserve compatibility` previews a patch bump, and `docs: update readme` does not create a tag.

## Local Usage

Run the action entrypoint directly:

```sh
just local-test
```

Functional tests:

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

Unit tests:

```sh
just unit-test
```

Example JSON output:

```json
{"currentVersion":"0.14.0","version":"0.14.1","createNewTag":"true","createNewRelease":"true","bump":"patch"}
```

`createNewTag` decides whether the workflow should create a semver tag.
`createNewRelease` decides whether the workflow should run full release work for the resolved bump level.
