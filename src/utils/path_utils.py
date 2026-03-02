"""Utility helpers for consistent dataset path handling.

All dataset-aware scripts should use these helpers so we can change the
storage location (for example /mnt/datasets) in a single place or override
it via the SO101_DATASETS_DIR environment variable.
"""

from __future__ import annotations

import os
from typing import Optional

_DATASETS_ENV_VAR = "SO101_DATASETS_DIR"
_DEFAULT_DATASETS_DIR = "/mnt/datasets"


def _expand_path(path: str) -> str:
    """Expand user (~) and environment variables for the provided path."""
    return os.path.expanduser(os.path.expandvars(path))


def get_datasets_dir() -> str:
    """Return the configured datasets directory (defaults to /mnt/datasets)."""
    configured = os.environ.get(_DATASETS_ENV_VAR, _DEFAULT_DATASETS_DIR)
    return _expand_path(configured)


def ensure_directory(path: Optional[str]) -> Optional[str]:
    """Create the target directory if it is provided and missing."""
    if path:
        os.makedirs(path, exist_ok=True)
    return path


def ensure_datasets_dir_exists() -> str:
    """Ensure the datasets directory exists and return its absolute path."""
    datasets_dir = get_datasets_dir()
    ensure_directory(datasets_dir)
    return datasets_dir


def build_dataset_path(filename: str) -> str:
    """Return an absolute path inside the datasets directory for filename."""
    if not filename:
        raise ValueError("filename must be provided when building a dataset path")
    filename = filename.lstrip("/\\")
    datasets_dir = ensure_datasets_dir_exists()
    return os.path.join(datasets_dir, filename)


def resolve_dataset_path(path: str) -> str:
    """Resolve any dataset path (absolute or relative) into an absolute path.

    Relative paths are anchored inside the configured datasets directory. Paths
    inside ./datasets or datasets/ are deduplicated so callers can continue
    passing the historical values (e.g. ./datasets/output.hdf5).
    """
    if not path:
        raise ValueError("data output path must be provided")

    expanded = _expand_path(path)

    if os.path.isabs(expanded):
        # Absolute path: just make sure the parent directory exists.
        parent = os.path.dirname(expanded) or expanded
        ensure_directory(parent)
        return expanded

    relative_path = expanded
    if relative_path.startswith("./"):
        relative_path = relative_path[2:]
    if relative_path.startswith(".\\"):
        relative_path = relative_path[2:]

    # Normalize legacy prefixes like datasets/ or ./datasets/
    for prefix in ("datasets/", "datasets\\"):
        if relative_path.startswith(prefix):
            relative_path = relative_path[len(prefix):]
            break

    relative_path = relative_path.lstrip("/\\")

    datasets_dir = ensure_datasets_dir_exists()
    resolved = os.path.normpath(os.path.join(datasets_dir, relative_path))
    ensure_directory(os.path.dirname(resolved))
    return resolved


__all__ = [
    "build_dataset_path",
    "ensure_datasets_dir_exists",
    "get_datasets_dir",
    "resolve_dataset_path",
]
