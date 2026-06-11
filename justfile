ACTION_DIR := justfile_directory()

local-test *args:
    #!/usr/bin/env bash
    set -euo pipefail

    repo_root="$(cd "{{ACTION_DIR}}/../../.." && pwd)"

    GITHUB_WORKSPACE="$repo_root" python3 "{{ACTION_DIR}}/get_next_version.py" "$@"


functional-test *args:
    #!/usr/bin/env bash
    set -euo pipefail

    python3 "{{ACTION_DIR}}/tests/test_functional_versioning.py" "$@"
