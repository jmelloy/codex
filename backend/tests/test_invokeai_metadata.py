"""Tests for InvokeAI PNG metadata extraction."""

import json
import os
import tempfile
import uuid

import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from sqlmodel import select

from codex.core.invokeai import extract_invokeai_metadata
from codex.core.metadata import MetadataParser
from codex.core.watcher import NotebookWatcher
from codex.db.database import get_notebook_session, init_notebook_db
from codex.db.models import Block

SAMPLE_METADATA = {
    "generation_mode": "sdxl_txt2img",
    "positive_prompt": "a robot reading a book",
    "negative_prompt": "blurry, low quality",
    "width": 1184,
    "height": 888,
    "seed": 591741300,
    "rand_device": "cpu",
    "cfg_scale": 5.0,
    "cfg_rescale_multiplier": 0.0,
    "steps": 30,
    "scheduler": "dpmpp_2m_sde",
    "model": {
        "key": "db73016a-176e-4d59-81d2-8e6278ed2399",
        "hash": "blake3:8967e7e6df2e97e08c61543779f7cc6b43b364287c375cd6dbff1627fd044312",
        "name": "lustifySDXLNSFW_endgame",
        "base": "sdxl",
        "type": "main",
    },
    "positive_style_prompt": "a robot reading a book",
    "negative_style_prompt": "",
    "app_version": "5.4.2",
}

SAMPLE_GRAPH = {
    "id": "sdxl_graph:7LKd5LqgBD",
    "nodes": {"noise:JhAzOy0T42": {"seed": 591741300, "type": "noise"}},
    "edges": [],
}


def _write_invokeai_png(path: str, metadata: dict | None = SAMPLE_METADATA, graph: dict | None = SAMPLE_GRAPH) -> None:
    """Write a small PNG embedding InvokeAI text chunks."""
    pnginfo = PngInfo()
    if metadata is not None:
        pnginfo.add_text("invokeai_metadata", json.dumps(metadata))
    if graph is not None:
        pnginfo.add_text("invokeai_graph", json.dumps(graph))
    img = Image.new("RGB", (32, 32), color="white")
    img.save(path, format="PNG", pnginfo=pnginfo)


def test_extract_invokeai_metadata_returns_promoted_fields():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "image.png")
        _write_invokeai_png(path)

        result = extract_invokeai_metadata(path)

    assert result is not None
    assert result["invokeai_prompt"] == SAMPLE_METADATA["positive_prompt"]
    assert result["invokeai_negative_prompt"] == SAMPLE_METADATA["negative_prompt"]
    assert result["invokeai_model"] == "lustifySDXLNSFW_endgame"
    assert result["invokeai_model_base"] == "sdxl"
    assert result["invokeai_model_hash"].startswith("blake3:")
    assert result["invokeai_seed"] == 591741300
    assert result["invokeai_scheduler"] == "dpmpp_2m_sde"
    assert result["invokeai_cfg_scale"] == 5.0
    assert result["invokeai_steps"] == 30
    assert result["invokeai_generation_mode"] == "sdxl_txt2img"
    assert result["invokeai_app_version"] == "5.4.2"
    assert result["invokeai"]["model"]["name"] == "lustifySDXLNSFW_endgame"
    assert result["invokeai_graph"]["id"] == "sdxl_graph:7LKd5LqgBD"


def test_extract_invokeai_metadata_non_png_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "image.jpg")
        Image.new("RGB", (10, 10)).save(path, format="JPEG")

        assert extract_invokeai_metadata(path) is None


def test_extract_invokeai_metadata_plain_png_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "image.png")
        Image.new("RGB", (10, 10)).save(path, format="PNG")

        assert extract_invokeai_metadata(path) is None


def test_extract_invokeai_metadata_handles_malformed_json():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "image.png")
        pnginfo = PngInfo()
        pnginfo.add_text("invokeai_metadata", "not valid json {")
        Image.new("RGB", (10, 10)).save(path, format="PNG", pnginfo=pnginfo)

        result = extract_invokeai_metadata(path)

    assert result is not None
    assert result["invokeai"] == "not valid json {"


def test_extract_all_metadata_includes_invokeai_fields():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "image.png")
        _write_invokeai_png(path)

        metadata = MetadataParser.extract_all_metadata(path)

    # Base image metadata still present
    assert metadata["format"] == "PNG"
    assert metadata["mode"] == "RGB"
    # InvokeAI fields merged in
    assert metadata["invokeai_model"] == "lustifySDXLNSFW_endgame"
    assert metadata["invokeai_seed"] == 591741300


@pytest.fixture
def temp_notebook():
    """Temp notebook with a queue-only watcher (no observer)."""
    temp_dir = tempfile.mkdtemp()
    init_notebook_db(temp_dir)

    watcher = NotebookWatcher(temp_dir, notebook_id=1)
    watcher.queue.BATCH_INTERVAL = 0.1
    watcher.queue.start()

    yield temp_dir, watcher

    try:
        watcher.queue.stop(timeout=1.0)
    except Exception:
        pass
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_watcher_stores_invokeai_properties(temp_notebook):
    temp_dir, watcher = temp_notebook
    name = f"{uuid.uuid4()}.png"
    path = os.path.join(temp_dir, name)
    _write_invokeai_png(path)

    watcher.enqueue_operation(path, None, "created", wait=True)

    rel_path = os.path.relpath(path, temp_dir)
    session = get_notebook_session(temp_dir)
    try:
        block = session.execute(
            select(Block).where(Block.notebook_id == 1, Block.path == rel_path)
        ).scalar_one_or_none()

        assert block is not None
        assert block.content_type == "image/png"

        properties = json.loads(block.properties)
        assert properties["invokeai_prompt"] == SAMPLE_METADATA["positive_prompt"]
        assert properties["invokeai_model"] == "lustifySDXLNSFW_endgame"
        assert properties["invokeai_seed"] == 591741300
        assert properties["invokeai_scheduler"] == "dpmpp_2m_sde"
        assert properties["invokeai"]["model"]["base"] == "sdxl"
    finally:
        session.close()
