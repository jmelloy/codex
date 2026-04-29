import re
import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

import models

logger = logging.getLogger(__name__)

# Terms common in diffusion prompts that carry little semantic meaning
DIFFUSION_STOP_WORDS = {
    "masterpiece", "best", "quality", "high", "ultra", "detailed", "realistic",
    "photorealistic", "4k", "8k", "hd", "uhd", "sharp", "focus", "beautiful",
    "amazing", "perfect", "awesome", "good", "great", "nice", "fine", "excellent",
    "intricate", "highly", "extremely", "very", "most", "highly detailed",
    "best quality", "masterpiece", "resolution", "render", "rendering",
    "cinematic", "lighting", "light", "shadow", "shadows", "studio", "professional",
    "illustration", "artwork", "art", "digital", "style", "styled", "trending",
    "artstation", "deviantart", "pixiv", "concept", "negative", "prompt",
    "lora", "checkpoint", "steps", "cfg", "sampler", "seed", "size",
}

SKLEARN_STOP_WORDS = "english"


def _clean_text(text: str) -> str:
    """Normalize text for TF-IDF."""
    text = text.lower()
    # Remove special characters but keep spaces
    text = re.sub(r"[<>\[\]{}()|\\/:;\"'`~@#$%^&*+=]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _build_corpus(db: Session, image_ids: Optional[List[int]] = None):
    """Return list of (image_id, text) tuples."""
    query = db.query(models.Image)
    if image_ids:
        query = query.filter(models.Image.id.in_(image_ids))

    corpus = []
    for img in query.all():
        parts = []
        if img.prompt:
            parts.append(img.prompt)
        if img.description:
            parts.append(img.description)
        text = " ".join(parts).strip()
        if text:
            corpus.append((img.id, _clean_text(text)))
    return corpus


def auto_tag_images(db: Session, image_ids: Optional[List[int]] = None, top_n: int = 10):
    """
    Run TF-IDF over prompts/descriptions and assign the top-N terms per image
    as tags in the database.
    """
    corpus = _build_corpus(db, image_ids)
    if len(corpus) < 2:
        logger.info("Not enough images with text for TF-IDF; skipping.")
        return

    ids = [c[0] for c in corpus]
    texts = [c[1] for c in corpus]

    try:
        vectorizer = TfidfVectorizer(
            stop_words=SKLEARN_STOP_WORDS,
            max_features=500,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b",
        )
        tfidf_matrix = vectorizer.fit_transform(texts)
    except Exception as e:
        logger.warning(f"TF-IDF vectorization failed: {e}")
        return

    feature_names = vectorizer.get_feature_names_out()

    # Pre-load or create Tag objects
    def get_or_create_tag(name: str) -> models.Tag:
        tag = db.query(models.Tag).filter(models.Tag.name == name).first()
        if not tag:
            tag = models.Tag(name=name)
            db.add(tag)
            db.flush()
        return tag

    for idx, image_id in enumerate(ids):
        img = db.query(models.Image).filter(models.Image.id == image_id).first()
        if img is None:
            continue

        row = tfidf_matrix[idx].toarray()[0]
        # Get indices sorted by TF-IDF score descending
        top_indices = np.argsort(row)[::-1]

        assigned = 0
        for fi in top_indices:
            if assigned >= top_n:
                break
            score = row[fi]
            if score == 0:
                break
            term = feature_names[fi]
            # Skip diffusion boilerplate terms
            if term in DIFFUSION_STOP_WORDS:
                continue
            # Skip purely numeric tokens
            if re.fullmatch(r"[0-9\s]+", term):
                continue
            tag = get_or_create_tag(term)
            if tag not in img.tags:
                img.tags.append(tag)
            assigned += 1

    db.commit()
    logger.info(f"Auto-tagged {len(ids)} images via TF-IDF.")
