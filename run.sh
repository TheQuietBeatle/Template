#!/usr/bin/env sh
# Start EGX Monitor (pass --browser to open in your browser instead of a desktop window).
cd "$(dirname "$0")/backend" && exec .venv/bin/python -m egx_monitor "$@"
