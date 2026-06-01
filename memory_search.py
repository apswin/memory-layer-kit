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
