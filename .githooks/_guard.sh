# Shared helper sourced by the git hooks in this directory.
# Locates a Python 3.9+ interpreter and runs the repository guard with it.

find_python() {
    for candidate in python3 python py; do
        if command -v "$candidate" >/dev/null 2>&1 &&
            "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 9))' >/dev/null 2>&1; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

run_guard() {
    if ! python_bin=$(find_python); then
        echo "repo-guard: Python 3.9 or newer is required to run the repository checks." >&2
        exit 1
    fi
    cd "$(git rev-parse --show-toplevel)" || exit 1
    exec "$python_bin" -m tools.repo_guard "$@"
}
