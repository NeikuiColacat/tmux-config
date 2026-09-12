#!/usr/bin/env bash
set -euo pipefail
if ! command -v python3 >/dev/null 2>&1; then
    echo '需要 Python 3.8+；Ubuntu/Debian 可安装 python3。' >&2
    exit 1
fi
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$repo_dir/scripts/install.py" "$@"
