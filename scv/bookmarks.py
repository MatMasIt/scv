"""Persistent bookmarks and slide annotations for SCV lectures."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def sidecar_path(source: Path | str) -> Path:
    """Return the mandatory ``.scvnotes`` path for a lecture."""
    source = Path(source)
    return source.with_suffix(".scvnotes")


def load(source: Path | str) -> dict:
    """Load a sidecar, returning an empty document when it does not exist."""
    path = sidecar_path(source)
    if not path.exists():
        return {"version": 1, "bookmarks": [], "notes": [], "annotations": {}}
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError(f"Unsupported bookmark file: {path}")
    data.setdefault("bookmarks", [])
    data.setdefault("notes", [])
    data.setdefault("annotations", {})
    return data


def save(source: Path | str, data: dict) -> Path:
    """Save study edits while preserving the separately saved play position."""
    path = sidecar_path(source)
    payload = {
        "version": 1,
        "bookmarks": data.get("bookmarks", []),
        "notes": data.get("notes", []),
        "annotations": data.get("annotations", {}),
    }
    if path.exists():
        current = load(source)
        if "progress" in current:
            payload["progress"] = current["progress"]
    return _write_sidecar(path, payload)


def load_progress(source: Path | str) -> dict | None:
    """Return a valid saved position, or ``None`` when progress is absent."""
    progress = load(source).get("progress")
    if not isinstance(progress, dict):
        return None
    position = progress.get("position_seconds")
    slide_index = progress.get("slide_index")
    if (
        isinstance(position, bool)
        or not isinstance(position, (int, float))
        or isinstance(slide_index, bool)
        or not isinstance(slide_index, int)
        or slide_index < 0
    ):
        return None
    try:
        position = float(position)
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(position) or position < 0:
        return None
    return {"position_seconds": position, "slide_index": slide_index}


def save_progress(
    source: Path | str,
    position_seconds: float,
    slide_index: int,
) -> Path:
    """Persist playback progress without serializing unsaved study edits."""
    if (
        isinstance(position_seconds, bool)
        or not isinstance(position_seconds, (int, float))
    ):
        raise ValueError("Playback position must be a finite non-negative number")
    try:
        position = float(position_seconds)
    except (OverflowError, ValueError) as exc:
        raise ValueError("Playback position must be a finite non-negative number") from exc
    if not math.isfinite(position) or position < 0:
        raise ValueError("Playback position must be a finite non-negative number")
    if (
        isinstance(slide_index, bool)
        or not isinstance(slide_index, int)
        or slide_index < 0
    ):
        raise ValueError("Slide index must be a non-negative integer")

    payload = load(source)
    payload["progress"] = {
        "position_seconds": round(position, 3),
        "slide_index": slide_index,
    }
    return _write_sidecar(sidecar_path(source), payload)


def _write_sidecar(path: Path, payload: dict) -> Path:
    """Atomically replace one sidecar JSON file."""
    part = path.with_suffix(path.suffix + ".part")
    part.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    part.replace(path)
    return path


def main(argv=None):
    """List bookmarks for a lecture from the command line."""
    parser = argparse.ArgumentParser(prog="scv-bookmarks")
    parser.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    for bookmark in load(args.file)["bookmarks"]:
        print(f'{bookmark["time"]:.3f}s\t{bookmark["label"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
