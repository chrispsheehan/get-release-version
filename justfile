ACTION_DIR := justfile_directory()

local-test *args:
    #!/usr/bin/env bash
    set -euo pipefail

    GITHUB_WORKSPACE="{{ACTION_DIR}}" python3 "{{ACTION_DIR}}/get_next_version.py" "$@"


functional-test *args:
    #!/usr/bin/env bash
    set -euo pipefail

    python3 "{{ACTION_DIR}}/tests/test_functional_versioning.py" "$@"


unit-test:
    #!/usr/bin/env bash
    set -euo pipefail

    python3 -m unittest discover -v -s "{{ACTION_DIR}}/tests" -p 'test_unit_*.py'
