# Personal AI memory layer

Build a portable, human-readable memory that any AI agent can read from and write to — a folder of Markdown notes (in Obsidian), synced to GitHub, with **local semantic search** on top so an agent can find things by *meaning*, not just keywords. Everything runs on your own machine; nothing is sent to a third party for the search itself.

It's organized as three layers:

- **Layer 1 — navigation map.** A root `_index.md` catalog, a descriptor in each folder, and YAML frontmatter on every note, so agents read targeted snippets instead of crawling everything.
- **Layer 2 — protocol.** A `MEMORY-PROTOCOL.md` rulebook every agent follows (which folders are off-limits, how to log changes, how to sign edits).
- **Layer 3 — RAG search.** A small local program (`memory_search.py`) that embeds your notes with the open-source `nomic-embed-text` model (via [Ollama](https://ollama.com)) and answers "what's most relevant to this question."

## Quick start

Hand `SETUP-GUIDE.md` to a capable AI coding agent (e.g. Claude Code, or a local agent that can run shell commands) and tell it to follow the phases. Steps that need a human (installing apps, creating a GitHub repo, granting permissions) are marked `[HUMAN]`; each phase ends with a checkpoint to confirm it worked. You can also follow it yourself — it's written in plain language.

## What's in here

- `SETUP-GUIDE.md` — the full, phase-by-phase build guide (Obsidian → GitHub → Layers 1-3), with checkpoints, file templates, and the search program embedded.
- `memory_search.py` — the Layer 3 search program (`index` and `search` commands).
- `requirements.txt` — its two Python dependencies (`numpy`, `requests`).
- `templates/` — drop-in files: `SKILL.md` + `run.sh` (the OpenClaw `memory-search` skill) and `vault.gitignore` (the `.gitignore` for your vault that keeps `50_Private/` off GitHub).

## For OpenClaw users

This kit was built to run inside [OpenClaw](https://openclaw.com), and the skill files are ready to drop in. After completing the setup guide through Phase 5 (the search program installed at `~/memory-search/`):

1. Copy the skill into place:
   ```
   mkdir -p ~/.openclaw/skills/memory-search
   cp templates/SKILL.md templates/run.sh ~/.openclaw/skills/memory-search/
   chmod +x ~/.openclaw/skills/memory-search/run.sh
   ```
2. Set `MEMORY_VAULT_PATH` in `memory_search.py` (or as an env var) to your vault, and make sure `nomic-embed-text` is pulled (`ollama pull nomic-embed-text`).
3. Schedule the re-index — easiest is to ask your agent: *"every 5 minutes run `~/memory-search/venv/bin/python ~/memory-search/memory_search.py index`."*
4. The `SKILL.md` description is written with aggressive routing language so the orchestrator picks `memory-search` for "what have I saved about X" questions instead of a web search.

Using a different agent (Claude Code, etc.)? Skip the skill files and just expose `memory_search.py search "<question>"` as a tool however that agent registers tools — the search program is identical.

## Requirements

- [Obsidian](https://obsidian.com), `git` + a GitHub account, Python 3.9+, and [Ollama](https://ollama.com) for the local embedding model.
- Default OS is macOS; Linux works with minor tweaks; on Windows use WSL.

## How it works (short version)

Your notes are the single source of truth. `memory_search.py index` reads them, splits each into chunks, turns each chunk into a 768-number "meaning vector" with `nomic-embed-text`, and stores everything in a single SQLite file. `memory_search.py search "your question"` embeds the question and returns the closest notes. The index is fully rebuildable from the notes — delete it and re-run `index` and it comes back. An agent calls `search` and writes the answer from the results (a retrieval-augmented-generation, or RAG, loop).

## Privacy

Embedding and search run entirely on your machine. A `50_Private/` folder is excluded from GitHub via `.gitignore` and never indexed by default, so private content stays local. (Note: if your agent uses a cloud model to write the final answer, the *retrieved* snippets are sent to that model at answer time — see the guide.)

## License

MIT — see `LICENSE`. Use it, fork it, adapt it.


