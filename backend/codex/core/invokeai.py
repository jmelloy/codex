"""InvokeAI PNG metadata extractor.

InvokeAI (https://github.com/invoke-ai/InvokeAI) embeds generation parameters
in PNG text chunks under two well-known keys:

- ``invokeai_metadata``: JSON with prompt, model, seed, scheduler, etc.
- ``invokeai_graph``: JSON describing the full node graph (large, rarely useful
  for display).

This module reads those chunks via Pillow's ``Image.info`` dict and returns a
flat metadata dict suitable for merging into :class:`codex.core.metadata.MetadataParser`'s
pipeline. Selected fields are promoted as top-level ``invokeai_*`` keys so they
are easy to search/index; the complete parsed payload is kept under the
``invokeai`` key for consumers that want the full picture.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)

METADATA_CHUNK = "invokeai_metadata"
GRAPH_CHUNK = "invokeai_graph"


def _parse_chunk(value: Any) -> Any:
    """Parse a PNG text chunk value as JSON, returning the raw value on failure."""
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _flatten(meta: dict[str, Any]) -> dict[str, Any]:
    """Promote commonly useful InvokeAI fields to ``invokeai_*`` top-level keys."""
    flat: dict[str, Any] = {}

    simple_fields = (
        "generation_mode",
        "positive_prompt",
        "negative_prompt",
        "positive_style_prompt",
        "negative_style_prompt",
        "seed",
        "scheduler",
        "cfg_scale",
        "cfg_rescale_multiplier",
        "steps",
        "rand_device",
        "app_version",
    )
    for field in simple_fields:
        if field in meta and meta[field] is not None:
            flat[f"invokeai_{field}"] = meta[field]

    model = meta.get("model")
    if isinstance(model, dict):
        if model.get("name"):
            flat["invokeai_model"] = model["name"]
        if model.get("base"):
            flat["invokeai_model_base"] = model["base"]
        if model.get("hash"):
            flat["invokeai_model_hash"] = model["hash"]
        if model.get("key"):
            flat["invokeai_model_key"] = model["key"]
        if model.get("type"):
            flat["invokeai_model_type"] = model["type"]

    return flat


def extract_invokeai_metadata(filepath: str) -> dict[str, Any] | None:
    """Extract InvokeAI metadata from a PNG file's text chunks.

    Returns a dict with promoted ``invokeai_*`` fields (prompt, model name,
    seed, scheduler, etc.) plus the full parsed payload under ``invokeai``.
    The node graph, when present, is stored under ``invokeai_graph``.

    Returns ``None`` for non-PNG files or PNGs without InvokeAI chunks.
    """
    if Path(filepath).suffix.lower() != ".png":
        return None

    try:
        with Image.open(filepath) as img:
            if img.format != "PNG":
                return None
            info = dict(img.info)
    except Exception as e:
        logger.debug(f"Could not open PNG {filepath} for InvokeAI metadata: {e}")
        return None

    raw_meta = info.get(METADATA_CHUNK)
    raw_graph = info.get(GRAPH_CHUNK)
    if raw_meta is None and raw_graph is None:
        return None

    result: dict[str, Any] = {}

    parsed_meta = _parse_chunk(raw_meta)
    if isinstance(parsed_meta, dict):
        result["invokeai"] = parsed_meta
        result.update(_flatten(parsed_meta))
    elif parsed_meta is not None:
        # Fall back to the raw string if it wasn't valid JSON.
        result["invokeai"] = parsed_meta

    parsed_graph = _parse_chunk(raw_graph)
    if parsed_graph is not None:
        result["invokeai_graph"] = parsed_graph

    return result or None
