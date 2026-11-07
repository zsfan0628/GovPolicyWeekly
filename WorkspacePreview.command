#!/bin/zsh
set -e
cd -- "$(dirname "$0")"
for python in .venv-release-check/bin/python .venv/bin/python; do
    if [[ -x "$python" ]]; then
        exec "$python" desktop_app.py --design-preview
    fi
done
printf 'No project Python environment found. Install the desktop dependencies first.\n'
read -r '?Press Return to close.'
