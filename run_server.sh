#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 &>/dev/null; then
    echo "[Error] Python3 is not installed."
    echo "Please install Python 3 first."
    exit 1
fi

exec python3 "$DIR/run_server.py"
