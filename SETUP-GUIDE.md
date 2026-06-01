---
summary: A complete, agent-executable guide for setting up this whole memory system from scratch — Obsidian vault, GitHub sync, the Layer 1-2 structure, and the Layer 3 local RAG search. Written so it can be handed to any capable AI agent (Claude Code, an OpenClaw-style agent, etc.) with notes marking the steps a human must do.
topic: [memory-layer, setup, rag]
updated: 2026-06-01
source: cowork
---

# Build your own AI memory layer — setup guide

Hand this file to a capable AI coding agent (one that can run shell commands and write files — e.g. Claude Code, or a local agent like OpenClaw). It will build a personal "horizontal memory" — a Markdown vault any AI can read and write — with semantic (meaning-based) search on top.

Steps marked **[HUMAN]** need a person (installing desktop apps, creating accounts, granting OS permissions). Everything else an agent can do. Each phase ends with a **CHECKPOINT** — do not proceed until it passes.

## Assumptions and placeholders

- Default OS: macOS (notes for Linux included). Windows: use WSL.
- Tools: `git`, Python 3.9+, and (for Layer 3) [Ollama](https://ollama.com) for local models.
- Replace these placeholders throughout:
  - `<VAULT>` — absolute path to the vault, e.g. `~/Documents/MyVault`
  - `<GITHUB_USER>` and `<REPO>` — your GitHub username and repo name
- The vault is the single source of truth. The search index is a derived copy that can always be rebuilt from the notes.

---

## Phase 0 — prerequisites

1. **[HUMAN]** Install Obsidian (obsidian.com), create a GitHub account, and confirm `git` and `python3` exist: `git --version && python3 --version`.
2. **[HUMAN]** For Layer 3 later: install Ollama (ollama.com) and confirm `ollama --version`.

CHECKPOINT 0: `git`, `python3`, and `ollama` all print versions; Obsidian opens.

---

## Phase 1 — vault and folder structure

1. **[HUMAN]** In Obsidian, create a new vault at `<VAULT>` (or pick an empty folder).
2. Create the PARA-style folders and placeholders:
   ```
   cd "<VAULT>"
   mkdir -p 00_Inbox 10_Projects 20_Areas 30_Resources 40_Daily 50_Private 90_AI_Memory/sources _meta
   touch 20_Areas/.gitkeep 40_Daily/.gitkeep _meta/.gitkeep
   ```
3. Seed three inbox notes so the vault isn't empty: `00_Inbox/ideas.md`, `00_Inbox/tasks.md`, `00_Inbox/reminders.md` (a heading and a line each is fine).

CHECKPOINT 1: `ls` shows all eight top-level folders; `00_Inbox/` has three `.md` files.

---

## Phase 2 — git and GitHub sync

1. Create `.gitignore` at the vault root (Appendix B). It MUST exclude `50_Private/`.
2. Initialize and make the first commit. (On a fresh machine git has no identity yet — set one, or the commit fails with "Author identity unknown".)
   ```
   cd "<VAULT>" && git init
   git config user.name "<YOUR NAME>" && git config user.email "<you@example.com>"   # skip if already set globally
   git add -A && git commit -m "initial vault"
   ```
3. **[HUMAN]** Create an empty private repo `<REPO>` on GitHub (no README). Then:
   ```
   git remote add origin https://github.com/<GITHUB_USER>/<REPO>.git
   git branch -M main && git push -u origin main
   ```
   (You'll authenticate with a GitHub Personal Access Token when prompted.)
4. **[HUMAN]** In Obsidian, install the community plugin "Obsidian Git" (by Vinzent03) and enable "auto commit-and-sync" every 5 minutes. This keeps the vault and GitHub in sync without manual commits.

CHECKPOINT 2: the repo appears on GitHub with your folders, and `50_Private/` is NOT there. Confirm with `git status` (clean) and by viewing the repo in a browser.

---

## Phase 3 — Layer 1: the navigation map

1. Create `_index.md` at the root: a catalog listing each top-level folder with a one-paragraph "when to use this" description. (Adapt the template in Appendix B.)
2. Create a descriptor in each top-level folder, e.g. `10_Projects/10_Projects.md`, describing what's in it and when to use vs avoid it. (Do NOT create one inside `_meta/` — treat `_meta/` as read-only.)
3. Add the canonical YAML frontmatter (Appendix B) to the top of every `.md` note. The `summary` field is the most important — it's what an agent reads to decide whether to open a file.

CHECKPOINT 3: every `.md` file begins with a `---` frontmatter block containing `summary`, `topic`, `updated`, `source`. Verify:
```
cd "<VAULT>" && for f in $(find . -name '*.md' -not -path './.git/*'); do head -1 "$f" | grep -q '^---$' || echo "MISSING: $f"; done
```
(No output = all good.)

---

## Phase 4 — Layer 2: the protocol

1. Create `MEMORY-PROTOCOL.md` at the root (Appendix B). It defines: zones (`50_Private/` off-limits, `_meta/` read-only, rest read+write), change logging, signatures `[YYYY-MM-DD][agent:<name>]`, and the read path.
2. Create the shared changelog `90_AI_Memory/_CHANGELOG.md` (append-only; every agent logs its file changes here).
3. Create `CLAUDE.md` and `AGENTS.md` at the root — short bootstrap files telling any agent to read `MEMORY-PROTOCOL.md` first, then `_index.md`. (Claude-family tools auto-load `CLAUDE.md`.)
4. **[HUMAN]** Add one line to your AI agent's system prompt: *"My memory is the vault at `<VAULT>`. Before reading or writing it, read MEMORY-PROTOCOL.md, then _index.md, and follow that protocol — including logging changes to 90_AI_Memory/_CHANGELOG.md, signed [agent:<yourname>]."*

CHECKPOINT 4: `MEMORY-PROTOCOL.md`, `90_AI_Memory/_CHANGELOG.md`, `CLAUDE.md`, `AGENTS.md` all exist at the expected paths.

---

## Phase 5 — Layer 3: the local RAG search

1. **[HUMAN]** Pull the embedding model: `ollama pull nomic-embed-text`. (Open source, ~270 MB, runs locally.)
2. **[HUMAN]** If your local runner limits loaded models, allow two so the embedder and your chat model don't evict each other (e.g. macOS: `launchctl setenv OLLAMA_MAX_LOADED_MODELS 2`, then restart Ollama).
3. Create the program at `~/memory-search/memory_search.py` — full source in Appendix A. Then set up its environment:
   ```
   mkdir -p ~/memory-search && cd ~/memory-search
   python3 -m venv venv && ./venv/bin/pip install numpy requests
   ```
4. Point it at your vault and build the first index:
   ```
   export MEMORY_VAULT_PATH="<VAULT>"
   ~/memory-search/venv/bin/python ~/memory-search/memory_search.py index
   ```
5. Schedule a re-index every few minutes so new notes are searchable. Prefer your AI agent's own scheduler if it has one (it runs with the right permissions); otherwise a cron entry works:
   ```
   */5 * * * * MEMORY_VAULT_PATH="<VAULT>" ~/memory-search/venv/bin/python ~/memory-search/memory_search.py index >/dev/null 2>&1
   ```
   (On macOS, system cron may need Full Disk Access to read your Documents folder — granting it, or using the agent's scheduler, avoids that.)
6. Expose search to your agent as a tool/skill that runs:
   `~/memory-search/venv/bin/python ~/memory-search/memory_search.py search "<the user's question>"`
   and returns the JSON. (OpenClaw: a `SKILL.md` + `run.sh` skill — templates in Appendix B. Other agents: register it however that agent registers tools. Give the tool an aggressive description so it's chosen for "what have I saved about X" questions over a web search.)

CHECKPOINT 5: `... memory_search.py search "test"` returns a JSON list of notes (not an error). The `index` line reports a note count > 0.

---

## Phase 6 — final acceptance test (end to end)

1. Through your agent, add a brand-new, unmistakable note (e.g. "idea: a purple zebra umbrella subscription service").
2. Wait for the next scheduled re-index (or run `index` once).
3. Ask the agent a question about it ("what's my purple zebra umbrella idea?") in a fresh conversation so it must *retrieve*, not recall.

CHECKPOINT 6 (the whole system): the agent answers correctly, and a direct
`... memory_search.py search "purple zebra umbrella"` returns that note at or near the top. If yes — write → auto-index → semantic retrieval all work, and the memory layer is live.

---

## How to know this guide actually works (validation)

Treat the guide itself as something to test, not just trust:

1. **Cold-start by a fresh agent.** Paste this file into a brand-new AI session with zero prior context and have it execute step by step. Every clarifying question it's forced to ask is a gap in the guide — fix the guide, repeat until it runs unattended.
2. **Clean environment.** Run it on a throwaway vault, a throwaway GitHub repo, and ideally a fresh machine/VM, so nothing pre-existing masks a missing step.
3. **Honor the checkpoints.** Each CHECKPOINT is an acceptance test with an expected result. The guide "works" only if all six pass on a clean run.
4. **Test the failure modes**, not just the happy path: no Ollama installed, no internet, Linux instead of macOS, an agent without shell access, a vault with spaces in its path. Each should either work or fail with a clear, documented message.
5. **Non-technical user test.** The real bar: a non-technical person hands this to their agent and reaches CHECKPOINT 6 without needing to understand the internals. If they get stuck, the wording — not the user — is the bug.

---

## Appendix B — file templates

**.gitignore**
```
50_Private/
.obsidian/workspace*
.trash/
.DS_Store
__pycache__/
*.pyc
index.db
```

**Canonical frontmatter (top of every note)**
```yaml
---
summary: <one to two sentences describing this note>
topic: [<tag>, <tag>]
updated: YYYY-MM-DD
source: <human | cowork | openclaw | claude-chat | unknown>
---
```

**MEMORY-PROTOCOL.md** — sections: Purpose; Zones (50_Private off-limits, _meta read-only, rest read+write); Change tracking (no append-only; log every create/edit/delete to 90_AI_Memory/_CHANGELOG.md; deletions must be logged); Signatures (`- [YYYY-MM-DD][agent:<name>] <note>`); Read path (index → folder descriptor → scan summaries → open matching note); Frontmatter schema (above).

**CLAUDE.md / AGENTS.md** — a few lines: "This folder is a personal memory vault. Before reading or writing, read MEMORY-PROTOCOL.md, then _index.md. Stay out of 50_Private/, treat _meta/ as read-only, log changes to 90_AI_Memory/_CHANGELOG.md signed [agent:<name>]."

**OpenClaw skill — `~/.openclaw/skills/memory-search/SKILL.md`**
```
---
name: memory-search
description: >-
  REQUIRED for ANY question about what the user has previously noted, saved, or
  decided in their vault/memory. Semantic search over the local notes. DO NOT use
  web_search for the user's own memory.
metadata:
  openclaw:
    emoji: "🧠"
    requires:
      bins: ["ollama"]
---
Runs memory_search.py search and returns the matching notes as JSON.
```

**`~/.openclaw/skills/memory-search/run.sh`**
```
#!/bin/bash
exec "$HOME/memory-search/venv/bin/python" "$HOME/memory-search/memory_search.py" search "$@"
```

---

## Appendix A — `memory_search.py` (create this file verbatim)

```python
#!/usr/bin/env python3
"""
memory_search.py - Layer 3 semantic search over your Obsidian vault.

Two commands:
  index   - read every markdown note, turn it into "meaning numbers" (embeddings),
            and store them. Incremental: only re-embeds notes whose file changed.
  search  - given a question, return the notes whose meaning is closest.

Embeddings come from a small model served by Ollama locally
(default: nomic-embed-text). Nothing leaves the machine.

Config via environment variables (all optional, sensible defaults):
  MEMORY_VAULT_PATH      path to the Obsidian vault to index
  MEMORY_DB_PATH         where to store the index (a single sqlite file)
  MEMORY_OLLAMA_HOST     default http://127.0.0.1:11434
  MEMORY_EMBED_MODEL     default nomic-embed-text
  MEMORY_INCLUDE_PRIVATE "1" to also index 50_Private (default: excluded)
  MEMORY_EMBED_BACKEND   "ollama" (default) or "stub" (offline self-test only)
"""
import os, re, sys, json, sqlite3, hashlib
import numpy as np

VAULT_PATH = os.environ.get("MEMORY_VAULT_PATH", os.path.expanduser(
    "~/ObsidianVault"))
DB_PATH = os.environ.get("MEMORY_DB_PATH", os.path.expanduser("~/memory-search/index.db"))
OLLAMA_HOST = os.environ.get("MEMORY_OLLAMA_HOST", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("MEMORY_EMBED_MODEL", "nomic-embed-text")
INCLUDE_PRIVATE = os.environ.get("MEMORY_INCLUDE_PRIVATE", "0") == "1"
EMBED_BACKEND = os.environ.get("MEMORY_EMBED_BACKEND", "ollama")

EXCLUDE_DIRS = {".git", ".obsidian", ".trash"}
CHUNK_CHARS = 1200          # ~1 paragraph-ish; small enough for precise matches
CHUNK_OVERLAP = 150         # keep a little context between chunks

# ---------- embeddings ----------
def embed_ollama(text):
    import requests
    # Try the newer /api/embed endpoint first, then fall back to /api/embeddings,
    # so this works across Ollama versions without the user having to care.
    try:
        r = requests.post(f"{OLLAMA_HOST}/api/embed",
                          json={"model": EMBED_MODEL, "input": text}, timeout=120)
        if r.status_code == 200:
            d = r.json()
            if d.get("embeddings"): return np.array(d["embeddings"][0], dtype=np.float32)
            if d.get("embedding"):  return np.array(d["embedding"], dtype=np.float32)
    except Exception:
        pass
    r = requests.post(f"{OLLAMA_HOST}/api/embeddings",
                      json={"model": EMBED_MODEL, "prompt": text}, timeout=120)
    r.raise_for_status()
    return np.array(r.json()["embedding"], dtype=np.float32)

def embed_stub(text):
    # Deterministic offline stand-in: hashes words into a small vector.
    # Only for self-testing the pipeline without Ollama; NOT semantic.
    v = np.zeros(256, dtype=np.float32)
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        h = int(hashlib.md5(w.encode()).hexdigest(), 16)
        v[h % 256] += 1.0
    n = np.linalg.norm(v)
    return v / n if n else v

def _apply_prefix(text, role):
    # nomic-embed-text expects task prefixes ("search_query:" for the question,
    # "search_document:" for indexed text). They noticeably improve matching,
    # especially for short, distinctive queries. Applied only for nomic models.
    if "nomic" in EMBED_MODEL.lower():
        tag = "search_query: " if role == "query" else "search_document: "
        return tag + text
    return text

def embed(text, role="document"):
    text = _apply_prefix(text, role)
    return embed_stub(text) if EMBED_BACKEND == "stub" else embed_ollama(text)

# ---------- helpers ----------
def read_frontmatter_summary(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            m = re.search(r'^summary:\s*(.+)$', text[3:end], re.MULTILINE)
            if m:
                return m.group(1).strip().strip('"')
    return ""

def strip_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end+4:]
    return text

def chunk_text(text):
    text = text.strip()
    if not text:
        return []
    # Split on blank lines first so each idea / bullet / paragraph becomes its
    # own chunk. This stops one specific item (e.g. a single startup idea in a
    # long list) from being diluted by everything around it. Blocks larger than
    # CHUNK_CHARS (e.g. transcript paragraphs) are then sub-split by length.
    chunks = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        if len(block) <= CHUNK_CHARS:
            chunks.append(block)
        else:
            i = 0
            while i < len(block):
                chunks.append(block[i:i+CHUNK_CHARS])
                i += CHUNK_CHARS - CHUNK_OVERLAP
    return chunks

def iter_md_files(vault):
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        rel_root = os.path.relpath(root, vault)
        if not INCLUDE_PRIVATE and (rel_root == "50_Private"
                                    or rel_root.startswith("50_Private" + os.sep)):
            continue
        for f in files:
            if f.endswith(".md"):
                yield os.path.join(root, f)

def vec_to_blob(v): return v.astype(np.float32).tobytes()
def blob_to_vec(b): return np.frombuffer(b, dtype=np.float32)

# ---------- db ----------
def db_connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS chunks(
        path TEXT, chunk_index INTEGER, mtime REAL,
        summary TEXT, text TEXT, embedding BLOB)""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_path ON chunks(path)")
    return con

# ---------- commands ----------
def cmd_index():
    con = db_connect()
    seen, new_files, updated, skipped = set(), 0, 0, 0
    for path in iter_md_files(VAULT_PATH):
        rel = os.path.relpath(path, VAULT_PATH)
        seen.add(rel)
        mtime = os.path.getmtime(path)
        row = con.execute("SELECT mtime FROM chunks WHERE path=? LIMIT 1", (rel,)).fetchone()
        if row and abs(row[0] - mtime) < 1e-6:
            skipped += 1
            continue
        with open(path, encoding="utf-8", errors="ignore") as fh:
            raw = fh.read()
        summary = read_frontmatter_summary(raw)
        body = strip_frontmatter(raw)
        # Index the summary as its own chunk (good for topical matches), plus each
        # body block on its own (good for specific content). The summary is NOT
        # prepended to body chunks — doing so previously diluted short, distinctive
        # chunks (e.g. a single idea) with the note's generic summary.
        entries = ([summary] if summary else []) + chunk_text(body)
        if not entries:
            entries = [rel]
        con.execute("DELETE FROM chunks WHERE path=?", (rel,))
        for idx, ch in enumerate(entries):
            emb = embed(ch, "document")
            con.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)",
                        (rel, idx, mtime, summary, ch, vec_to_blob(emb)))
        if row: updated += 1
        else:   new_files += 1
    existing = {r[0] for r in con.execute("SELECT DISTINCT path FROM chunks")}
    removed = existing - seen
    for rel in removed:
        con.execute("DELETE FROM chunks WHERE path=?", (rel,))
    con.commit()
    total = con.execute("SELECT COUNT(DISTINCT path) FROM chunks").fetchone()[0]
    print(f"indexed: {new_files} new, {updated} updated, {skipped} unchanged, "
          f"{len(removed)} removed. {total} notes in index ({DB_PATH}).")

def cmd_search(query, top_k=5):
    con = db_connect()
    rows = con.execute("SELECT path, summary, text, embedding FROM chunks").fetchall()
    if not rows:
        print("Index is empty. Run: memory_search.py index"); return
    q = embed(query, "query")
    qn = q / (np.linalg.norm(q) or 1)
    best = {}
    for path, summary, text, blob in rows:
        v = blob_to_vec(blob)
        score = float(np.dot(qn, v / (np.linalg.norm(v) or 1)))
        if path not in best or score > best[path][0]:
            best[path] = (score, summary, text[:240].replace("\n", " ").strip())
    ranked = sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)[:top_k]
    out = [{"path": p, "score": round(s, 3), "summary": sm, "snippet": sn}
           for p, (s, sm, sn) in ranked]
    print(json.dumps(out, indent=2, ensure_ascii=False))

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("index", "search"):
        print("usage: memory_search.py index | search <query>"); sys.exit(1)
    if sys.argv[1] == "index":
        cmd_index()
    else:
        if len(sys.argv) < 3:
            print("usage: memory_search.py search <query>"); sys.exit(1)
        cmd_search(" ".join(sys.argv[2:]))

if __name__ == "__main__":
    main()
```
