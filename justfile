set positional-arguments

ACTION_DIR := justfile_directory()

local-test *args:
    #!/usr/bin/env bash
    set -euo pipefail

    repo_root="{{ACTION_DIR}}"
    git_config_global="$(mktemp)"
    trap 'rm -f "$git_config_global"' EXIT

    GITHUB_WORKSPACE="$repo_root" GIT_CONFIG_GLOBAL="$git_config_global" python3 "{{ACTION_DIR}}/get_next_version.py" "$@"


functional-test *args:
    #!/usr/bin/env bash
    set -euo pipefail

    python3 "{{ACTION_DIR}}/tests/test_functional_versioning.py" "$@"


unit-test *args:
    #!/usr/bin/env bash
    set -euo pipefail

    python3 -m unittest discover -v -s "{{ACTION_DIR}}/tests" -p 'test_unit_*.py' "$@"
