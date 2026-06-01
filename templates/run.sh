#!/bin/bash
# OpenClaw skill wrapper for memory-search.
# Install: copy this file and SKILL.md into ~/.openclaw/skills/memory-search/
# then: chmod +x ~/.openclaw/skills/memory-search/run.sh
# If your vault isn't at memory_search.py's default, export MEMORY_VAULT_PATH.
exec "$HOME/memory-search/venv/bin/python" "$HOME/memory-search/memory_search.py" search "$@"
