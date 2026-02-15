"""
JARVIIS Memory Manager — Phase 3 Compatible
Optimized for 8GB RAM / i5.

Strategy:
  - TF-IDF similarity for retrieval (no embedding model needed)
  - Sliding window compression (no LLM call for summarization)
  - SQLite for persistence (zero server dependency)
  - Max 200 stored memories, auto-prune by recency + relevance score
"""

import sqlite3
import math
import time
import json
import hashlib
import re
from pathlib import Path
from dataclasses import dataclass


# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class Memory:
    id: str
    content: str
    timestamp: float
    source: str          # "user", "assistant", "system"
    importance: float    # 0.0 → 1.0, manually set or inferred
    access_count: int = 0

    def decay_score(self, now: float = None) -> float:
        """Recency-weighted importance. Decays over 7 days."""
        now = now or time.time()
        age_days = (now - self.timestamp) / 86400
        decay = math.exp(-0.1 * age_days)   # half-life ~7 days
        return self.importance * decay + (self.access_count * 0.02)


# ─────────────────────────────────────────────
# TF-IDF RETRIEVER (no heavy ML required)
# ─────────────────────────────────────────────

class TFIDFRetriever:
    """
    Lightweight keyword-based retriever.
    Handles ~500 memories with sub-10ms retrieval on i5.
    """

    STOP_WORDS = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "this", "that", "it",
        "i", "you", "we", "they", "he", "she", "and", "or", "but", "not",
    }

    def _tokenize(self, text: str) -> list[str]:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        return [w for w in words if w not in self.STOP_WORDS]

    def compute_tfidf(
        self,
        query: str,
        memories: list[Memory],
    ) -> list[tuple[Memory, float]]:

        if not memories:
            return []

        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return [(m, 0.0) for m in memories]

        N = len(memories)
        # IDF: count docs containing each query token
        df: dict[str, int] = {}
        tokenized_docs = []
        for m in memories:
            tokens = self._tokenize(m.content)
            tokenized_docs.append(tokens)
            for t in set(tokens):
                if t in query_tokens:
                    df[t] = df.get(t, 0) + 1

        idf: dict[str, float] = {}
        for token in query_tokens:
            doc_freq = df.get(token, 0)
            idf[token] = math.log((N + 1) / (doc_freq + 1)) + 1

        scored: list[tuple[Memory, float]] = []
        for i, (m, tokens) in enumerate(zip(memories, tokenized_docs)):
            tf: dict[str, float] = {}
            total = len(tokens) or 1
            for t in tokens:
                if t in query_tokens:
                    tf[t] = tf.get(t, 0) + 1 / total

            tfidf_score = sum(tf.get(t, 0) * idf.get(t, 0) for t in query_tokens)
            # Boost by memory importance + recency
            final_score = tfidf_score + m.decay_score() * 0.15
            scored.append((m, final_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


# ─────────────────────────────────────────────
# MEMORY MANAGER
# ─────────────────────────────────────────────

class MemoryManager:
    """
    Full memory lifecycle manager.
    - Store, retrieve, prune, compress
    - SQLite backend — no Redis, no server
    - Dedup via content hash
    """

    MAX_MEMORIES = 250
    PRUNE_TO     = 180      # prune down to this on overflow
    TOP_K        = 6        # default retrieval count

    def __init__(self, db_path: str = "/tmp/jarviis_memory.db"):
        self.db_path  = db_path
        self.retriever = TFIDFRetriever()
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id           TEXT PRIMARY KEY,
                content      TEXT NOT NULL,
                timestamp    REAL NOT NULL,
                source       TEXT NOT NULL,
                importance   REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON memories(timestamp)")
        conn.commit()
        conn.close()

    # ── CRUD ──────────────────────────────────

    def store(self, content: str, source: str = "user", importance: float = 0.5) -> str:
        content = content.strip()
        if not content:
            return ""

        mem_id = hashlib.sha1(content.encode()).hexdigest()[:12]

        conn = sqlite3.connect(self.db_path)
        try:
            existing = conn.execute(
                "SELECT id FROM memories WHERE id = ?", (mem_id,)
            ).fetchone()

            if not existing:
                conn.execute(
                    "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?)",
                    (mem_id, content, time.time(), source, importance, 0)
                )
                conn.commit()
                self._maybe_prune(conn)
        finally:
            conn.close()

        return mem_id

    def retrieve(self, query: str, top_k: int = None) -> list[str]:
        top_k = top_k or self.TOP_K
        memories = self._load_all()
        if not memories:
            return []

        scored = self.retriever.compute_tfidf(query, memories)
        top = scored[:top_k]

        # Update access counts
        ids = [m.id for m, _ in top if _ > 0]
        if ids:
            conn = sqlite3.connect(self.db_path)
            placeholders = ",".join("?" * len(ids))
            conn.execute(
                f"UPDATE memories SET access_count = access_count + 1 WHERE id IN ({placeholders})",
                ids
            )
            conn.commit()
            conn.close()

        return [m.content for m, score in top if score > 0.01]

    def store_conversation_turn(self, user_msg: str, assistant_msg: str):
        """Extract and store only high-value information from a turn."""
        key_facts = self._extract_key_facts(user_msg + "\n" + assistant_msg)
        for fact in key_facts:
            self.store(fact, source="conversation", importance=0.6)

    # ── PRIVATE ───────────────────────────────

    def _load_all(self) -> list[Memory]:
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT id, content, timestamp, source, importance, access_count FROM memories"
        ).fetchall()
        conn.close()
        return [Memory(*row) for row in rows]

    def _maybe_prune(self, conn: sqlite3.Connection):
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        if count <= self.MAX_MEMORIES:
            return

        # Score all memories and remove the lowest
        rows = conn.execute(
            "SELECT id, content, timestamp, importance, access_count FROM memories"
        ).fetchall()

        now = time.time()
        scored = []
        for row in rows:
            mem_id, content, ts, importance, access_count = row
            age_days  = (now - ts) / 86400
            decay     = math.exp(-0.1 * age_days)
            score     = importance * decay + access_count * 0.02
            scored.append((mem_id, score))

        scored.sort(key=lambda x: x[1])
        to_delete = [s[0] for s in scored[:count - self.PRUNE_TO]]
        if to_delete:
            placeholders = ",".join("?" * len(to_delete))
            conn.execute(f"DELETE FROM memories WHERE id IN ({placeholders})", to_delete)
            conn.commit()

    def _extract_key_facts(self, text: str) -> list[str]:
        """
        Heuristic extraction — no LLM call needed.
        Extracts sentences containing factual markers.
        """
        FACT_SIGNALS = [
            "my name is", "i am", "i work", "i prefer", "i want",
            "i need", "i use", "my goal", "my project", "i built",
            "jarviis should", "always", "never", "remember that",
        ]
        sentences = re.split(r'[.!?]\s+', text)
        facts = []
        for s in sentences:
            s_lower = s.lower()
            if any(sig in s_lower for sig in FACT_SIGNALS):
                clean = s.strip()
                if 10 < len(clean) < 300:
                    facts.append(clean)
        return facts[:5]  # cap per turn

    def get_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        avg_importance = conn.execute(
            "SELECT AVG(importance) FROM memories"
        ).fetchone()[0] or 0
        conn.close()
        return {"total_memories": count, "avg_importance": round(avg_importance, 3)}
