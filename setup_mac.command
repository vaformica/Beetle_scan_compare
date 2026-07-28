#!/bin/zsh
set -e

cd -- "$(dirname -- "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools
.venv/bin/python -m pip install .

echo
echo "Installation complete. Double-click run_app.command to start."
read -k 1 "?Press any key to close this window."
