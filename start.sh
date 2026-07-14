#!/usr/bin/env bash
# Red Arc Ops Tool — start the local app (macOS/Linux dev).
set -e
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
python3 -m app.server
