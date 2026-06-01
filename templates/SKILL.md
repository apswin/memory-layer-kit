---
name: memory-search
description: >-
  REQUIRED for ANY question about what the user has previously noted, saved,
  decided, or captured in their notes / vault / memory. Performs semantic
  (meaning-based) search over the local Obsidian vault and returns the most
  relevant notes as JSON. Use for "what did I save about X", "do I have anything
  on X", the user's projects, ideas, tasks, reminders, or previously saved
  articles/videos. DO NOT use web_search for the user's own memory. DO NOT use a
  generic agent-memory skill for vault content — this skill searches the
  Obsidian vault specifically.
metadata:
  openclaw:
    emoji: "🧠"
    requires:
      bins: ["ollama"]
---

# memory-search

Semantic search over the user's Obsidian vault (Layer 3 of the memory layer).
Calls `memory_search.py search "<query>"` and returns the top matching notes as
JSON (`path`, `score`, `summary`, `snippet`). Read the summary/snippet of each
hit to decide which full note(s) to open. Keep distinct from any generic
agent-memory skill — this one searches the Obsidian vault.
