#!/bin/zsh
set -e

cd -- "$(dirname -- "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo "The app is not installed yet."
  echo "Double-click setup_mac.command first."
  read -k 1 "?Press any key to close this window."
  exit 1
fi

.venv/bin/python -m beetle_compare
