from __future__ import annotations

import sqlite3
from pathlib import Path

from draftlens_api.evidence.types import EvidenceChunk


class EvidenceIndex:
    """
    Local SQLite FTS5 index over evidence chunks (no external vector DB).
    If FTS5 is unavailable, `fts_enabled` is False and search() returns [].
    """

    def __init__(self, db_path: Path, *, fts_enabled: bool) -> None:
        self._db_path = db_path
        self.fts_enabled = fts_enabled

    @classmethod
    def build(cls, db_path: Path, chunks: list[EvidenceChunk]) -> EvidenceIndex:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if db_path.exists():
            db_path.unlink()
        if not chunks:
            return cls(db_path, fts_enabled=False)
        fts_ok = _fts5_supported()
        if not fts_ok:
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    "CREATE TABLE evidence_fallback (chunk_id TEXT PRIMARY KEY, source_label TEXT, body TEXT)"
                )
                for c in chunks:
                    conn.execute(
                        "INSERT INTO evidence_fallback(chunk_id, source_label, body) VALUES (?,?,?)",
                        (c.chunk_id, c.source_label, c.text),
                    )
                conn.commit()
            finally:
                conn.close()
            return cls(db_path, fts_enabled=False)

        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE evidence_fts USING fts5("
                "chunk_id UNINDEXED, source_label UNINDEXED, body, tokenize='porter'"
                ")"
            )
            for c in chunks:
                conn.execute(
                    "INSERT INTO evidence_fts(chunk_id, source_label, body) VALUES (?,?,?)",
                    (c.chunk_id, c.source_label, c.text),
                )
            conn.commit()
        finally:
            conn.close()
        return cls(db_path, fts_enabled=True)

    def search(self, query: str, *, limit: int = 24) -> list[tuple[str, str, str, float]]:
        """Return (chunk_id, source_label, body, score_0_1) best-first."""
        if not self.fts_enabled or not query.strip():
            return []
        conn = sqlite3.connect(str(self._db_path))
        try:
            cur = conn.execute(
                "SELECT chunk_id, source_label, body, bm25(evidence_fts) AS b "
                "FROM evidence_fts WHERE evidence_fts MATCH ? ORDER BY b ASC LIMIT ?",
                (query, limit),
            )
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()
        out: list[tuple[str, str, str, float]] = []
        if not rows:
            return out
        raw_scores = [float(r[3]) for r in rows]
        lo, hi = min(raw_scores), max(raw_scores)
        span = hi - lo or 1.0
        for r in rows:
            cid, lab, body, bm = r[0], r[1], r[2], float(r[3])
            # bm25 ascending is better; map to 0..1 higher is better
            norm = 1.0 - (bm - lo) / span
            out.append((str(cid), str(lab), str(body), max(0.0, min(1.0, norm))))
        return out


def _fts5_supported() -> bool:
    con = sqlite3.connect(":memory:")
    try:
        con.execute("CREATE VIRTUAL TABLE _probe USING fts5(a)")
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        con.close()
