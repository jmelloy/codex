"""Page-level vectorization and embedding service.

Uses litellm to generate embeddings for page content (title, properties,
description, child text) and stores them in sqlite-vec virtual tables
for fast cosine-similarity search.
"""

from __future__ import annotations

import json
import logging
import os
import struct
import threading
from pathlib import Path

import numpy as np
from sqlmodel import Session, select

from codex.db.models.notebook import Block

logger = logging.getLogger(__name__)

# Default embedding model — can be overridden via env var
EMBEDDING_MODEL = os.getenv("CODEX_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("CODEX_EMBEDDING_DIMENSIONS", "1536"))

# Lock for serialising sqlite-vec DDL across threads
_vec_init_lock = threading.Lock()


def _serialize_f32(vec: list[float] | np.ndarray) -> bytes:
    """Serialize a vector to little-endian float32 bytes for sqlite-vec."""
    if isinstance(vec, np.ndarray):
        return vec.astype(np.float32).tobytes()
    return struct.pack(f"<{len(vec)}f", *vec)


def _deserialize_f32(blob: bytes) -> np.ndarray:
    """Deserialize sqlite-vec float32 bytes to numpy array."""
    return np.frombuffer(blob, dtype=np.float32)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


# ---------------------------------------------------------------------------
# FTS5 + vec0 table helpers
# ---------------------------------------------------------------------------


def ensure_search_tables(engine) -> None:
    """Create FTS5 and vec0 virtual tables if they don't already exist.

    Must be called once per notebook database (idempotent).
    """
    import sqlite3

    import sqlite_vec

    with _vec_init_lock:
        raw_url = str(engine.url)
        db_path = raw_url.replace("sqlite:///", "")

        conn = sqlite3.connect(db_path)
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)

            # FTS5 virtual table for keyword search on pages
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                    block_id,
                    title,
                    description,
                    properties,
                    content,
                    tokenize='porter unicode61'
                )
                """
            )

            # Vec0 virtual table for vector similarity search
            conn.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS page_embeddings USING vec0(
                    block_id TEXT PRIMARY KEY,
                    embedding float[{EMBEDDING_DIMENSIONS}]
                )
                """
            )

            conn.commit()
        finally:
            conn.close()


def _get_raw_connection(engine):
    """Get a raw sqlite3 connection with sqlite-vec loaded."""
    import sqlite3

    import sqlite_vec

    raw_url = str(engine.url)
    db_path = raw_url.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


# ---------------------------------------------------------------------------
# Text assembly for a page
# ---------------------------------------------------------------------------


def build_page_text(block: Block, notebook_path: str, session: Session) -> str:
    """Build a searchable text representation of a page.

    Combines: title, description, properties values, and child block content.
    """
    parts: list[str] = []

    if block.title:
        parts.append(block.title)

    if block.description:
        parts.append(block.description)

    # Flatten properties values
    if block.properties:
        try:
            props = json.loads(block.properties) if isinstance(block.properties, str) else block.properties
            for key, val in props.items():
                if isinstance(val, str):
                    parts.append(f"{key}: {val}")
                elif isinstance(val, list):
                    parts.append(f"{key}: {', '.join(str(v) for v in val)}")
                else:
                    parts.append(f"{key}: {val}")
        except (json.JSONDecodeError, TypeError):
            pass

    # Gather child block content (text files under this page)
    children = (
        session.execute(
            select(Block).where(
                Block.notebook_id == block.notebook_id,
                Block.parent_block_id == block.block_id,
                Block.block_type != "page",
            )
        )
        .scalars()
        .all()
    )

    nb_path = Path(notebook_path)
    for child in children:
        if child.content_type and child.content_type.startswith("text/"):
            file_path = nb_path / child.path
            if file_path.exists():
                try:
                    text = file_path.read_text(encoding="utf-8", errors="replace")[:8000]
                    parts.append(text)
                except Exception:
                    pass

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# FTS index operations
# ---------------------------------------------------------------------------


def index_page_fts(engine, block: Block, page_text: str) -> None:
    """Insert or update the FTS5 index for a page."""
    import sqlite3

    raw_url = str(engine.url)
    db_path = raw_url.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    try:
        # Delete existing entry
        conn.execute("DELETE FROM pages_fts WHERE block_id = ?", (block.block_id,))

        props_text = ""
        if block.properties:
            try:
                props = json.loads(block.properties) if isinstance(block.properties, str) else block.properties
                props_text = " ".join(f"{k} {v}" for k, v in props.items() if isinstance(v, str))
            except (json.JSONDecodeError, TypeError):
                pass

        conn.execute(
            "INSERT INTO pages_fts (block_id, title, description, properties, content) VALUES (?, ?, ?, ?, ?)",
            (
                block.block_id,
                block.title or "",
                block.description or "",
                props_text,
                page_text,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_page_fts(engine, block_id: str) -> None:
    """Remove a page from the FTS5 index."""
    import sqlite3

    raw_url = str(engine.url)
    db_path = raw_url.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM pages_fts WHERE block_id = ?", (block_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Embedding operations
# ---------------------------------------------------------------------------


def generate_embedding(text: str) -> list[float] | None:
    """Generate an embedding vector using litellm."""
    if not text.strip():
        return None

    try:
        import litellm

        response = litellm.embedding(model=EMBEDDING_MODEL, input=[text[:8000]])
        return response.data[0]["embedding"]
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")
        return None


def store_embedding(engine, block_id: str, embedding: list[float]) -> None:
    """Store a page embedding in the vec0 virtual table."""
    conn = _get_raw_connection(engine)
    try:
        # Delete existing
        conn.execute("DELETE FROM page_embeddings WHERE block_id = ?", (block_id,))
        conn.execute(
            "INSERT INTO page_embeddings (block_id, embedding) VALUES (?, ?)",
            (block_id, _serialize_f32(embedding)),
        )
        conn.commit()
    finally:
        conn.close()


def delete_embedding(engine, block_id: str) -> None:
    """Remove a page embedding."""
    conn = _get_raw_connection(engine)
    try:
        conn.execute("DELETE FROM page_embeddings WHERE block_id = ?", (block_id,))
        conn.commit()
    finally:
        conn.close()


def search_by_vector(engine, query_embedding: list[float], limit: int = 20) -> list[tuple[str, float]]:
    """Search for similar pages using vector similarity.

    Returns list of (block_id, distance) tuples, sorted by ascending distance.
    """
    conn = _get_raw_connection(engine)
    try:
        rows = conn.execute(
            """
            SELECT block_id, distance
            FROM page_embeddings
            WHERE embedding MATCH ?
            ORDER BY distance
            LIMIT ?
            """,
            (_serialize_f32(query_embedding), limit),
        ).fetchall()
        return [(row[0], row[1]) for row in rows]
    finally:
        conn.close()


def search_by_fts(engine, query: str, limit: int = 20) -> list[tuple[str, float]]:
    """Search pages using FTS5 full-text search.

    Returns list of (block_id, rank) tuples.
    """
    import sqlite3

    raw_url = str(engine.url)
    db_path = raw_url.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    try:
        # Use FTS5 rank function; boost title and description
        rows = conn.execute(
            """
            SELECT block_id, rank
            FROM pages_fts
            WHERE pages_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        return [(row[0], row[1]) for row in rows]
    except Exception as e:
        logger.warning(f"FTS search failed: {e}")
        return []
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Hybrid search
# ---------------------------------------------------------------------------


def hybrid_search(
    engine,
    query: str,
    limit: int = 20,
    use_vectors: bool = True,
) -> list[tuple[str, float]]:
    """Perform hybrid FTS + vector search, returning merged results.

    Returns list of (block_id, combined_score) sorted by descending score.
    """
    # FTS results
    fts_results = search_by_fts(engine, query, limit=limit * 2)

    # Normalise FTS scores (rank is negative, more negative = better)
    fts_scores: dict[str, float] = {}
    if fts_results:
        max_rank = max(abs(r[1]) for r in fts_results) or 1.0
        for block_id, rank in fts_results:
            # Convert rank to 0-1 score (higher is better)
            fts_scores[block_id] = abs(rank) / max_rank

    vec_scores: dict[str, float] = {}
    if use_vectors:
        query_embedding = generate_embedding(query)
        if query_embedding:
            vec_results = search_by_vector(engine, query_embedding, limit=limit * 2)
            if vec_results:
                max_dist = max(r[1] for r in vec_results) or 1.0
                for block_id, distance in vec_results:
                    # Convert distance to similarity score (higher is better)
                    vec_scores[block_id] = 1.0 - (distance / max_dist) if max_dist > 0 else 0.0

    # Merge with weighted combination (FTS 0.4, vector 0.6)
    all_ids = set(fts_scores.keys()) | set(vec_scores.keys())
    combined: list[tuple[str, float]] = []
    for block_id in all_ids:
        fts_s = fts_scores.get(block_id, 0.0)
        vec_s = vec_scores.get(block_id, 0.0)
        score = 0.4 * fts_s + 0.6 * vec_s
        # If only FTS matched (no vectors), give full FTS weight
        if block_id not in vec_scores and block_id in fts_scores:
            score = fts_s
        combined.append((block_id, score))

    combined.sort(key=lambda x: x[1], reverse=True)
    return combined[:limit]


# ---------------------------------------------------------------------------
# High-level: index a single page
# ---------------------------------------------------------------------------


def vectorize_page(engine, block: Block, notebook_path: str, session: Session) -> None:
    """Build FTS + vector index for a single page block."""
    ensure_search_tables(engine)

    page_text = build_page_text(block, notebook_path, session)

    # Always index FTS (fast, no API call)
    index_page_fts(engine, block, page_text)

    # Generate and store embedding (async-safe, but may be slow)
    embedding = generate_embedding(page_text)
    if embedding:
        store_embedding(engine, block.block_id, embedding)


def vectorize_all_pages(engine, notebook_id: int, notebook_path: str, session: Session) -> int:
    """Vectorize all page blocks in a notebook. Returns count of pages indexed."""
    ensure_search_tables(engine)

    pages = (
        session.execute(select(Block).where(Block.notebook_id == notebook_id, Block.block_type == "page")).scalars().all()
    )

    count = 0
    for page in pages:
        try:
            vectorize_page(engine, page, notebook_path, session)
            count += 1
        except Exception as e:
            logger.warning(f"Failed to vectorize page {page.block_id}: {e}")

    logger.info(f"Vectorized {count}/{len(pages)} pages for notebook {notebook_id}")
    return count


def remove_page_index(engine, block_id: str) -> None:
    """Remove both FTS and vector index for a page."""
    try:
        delete_page_fts(engine, block_id)
    except Exception:
        pass
    try:
        delete_embedding(engine, block_id)
    except Exception:
        pass
