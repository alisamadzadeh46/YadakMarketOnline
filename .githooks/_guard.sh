# Shared helper sourced by the git hooks in this directory.
# Locates a Python 3.9+ interpreter and runs the repository guard with it.
#
# Interpreters are tried in this order:
#   1. the one configured with: git config repo-guard.python "C:/path/to/python.exe"
#   2. a virtual environment inside the repository (venv/ or .venv/)
#   3. python3, python and the Windows "py" launcher found on the PATH

is_usable_python() {
    "$1" -c 'import sys; sys.exit(sys.version_info < (3, 9))' >/dev/null 2>&1
}

find_python() {
    configured=$(git config --get repo-guard.python)
    for candidate in "$configured" \
        venv/Scripts/python.exe .venv/Scripts/python.exe venv/bin/python .venv/bin/python \
        python3 python py; do
        if [ -n "$candidate" ] && is_usable_python "$candidate"; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

run_guard() {
    cd "$(git rev-parse --show-toplevel)" || exit 1
    if ! python_bin=$(find_python); then
        echo "repo-guard: Python 3.9 or newer was not found. Point the hooks to an interpreter with:" >&2
        echo '    git config repo-guard.python "C:/path/to/python.exe"' >&2
        exit 1
    fi
    exec "$python_bin" -m tools.repo_guard "$@"
}
