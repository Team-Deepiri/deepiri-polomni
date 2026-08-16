"""Narrow platform layer for durable cache file transactions."""

from __future__ import annotations

import os
import secrets
import shutil
import tempfile
from pathlib import Path


if os.name == "nt":  # pragma: no cover - exercised by native Windows CI
    import ctypes
    from ctypes import wintypes

    _MOVEFILE_REPLACE_EXISTING = 0x1
    _MOVEFILE_WRITE_THROUGH = 0x8
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _move_file_ex = _kernel32.MoveFileExW
    _move_file_ex.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    _move_file_ex.restype = wintypes.BOOL


def atomic_replace(source: Path, destination: Path) -> None:
    """Atomically publish *source* at *destination* on the local filesystem."""
    source = Path(source)
    destination = Path(destination)
    if os.name != "nt":
        os.replace(source, destination)
        return

    flags = _MOVEFILE_REPLACE_EXISTING | _MOVEFILE_WRITE_THROUGH
    if not _move_file_ex(str(source), str(destination), flags):
        raise ctypes.WinError(ctypes.get_last_error())


def sync_directory(path: Path) -> None:
    """Persist directory-entry changes where a separate directory sync is required."""
    if os.name == "nt":
        # MoveFileExW with MOVEFILE_WRITE_THROUGH persists Windows publications.
        return
    if os.name != "posix":
        raise OSError(f"Durable cache transactions are unsupported on os.name={os.name!r}")

    directory_flag = getattr(os, "O_DIRECTORY", None)
    if directory_flag is None:
        raise OSError("This POSIX platform does not expose O_DIRECTORY")
    fd = os.open(str(path), os.O_RDONLY | directory_flag)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _copy_file_durably(source: Path, destination: Path) -> None:
    """Publish a fully flushed copy without exposing an incomplete backup."""
    temporary: Path | None = None
    try:
        with source.open("rb") as source_handle, tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as destination_handle:
            temporary = Path(destination_handle.name)
            shutil.copyfileobj(source_handle, destination_handle)
            destination_handle.flush()
            os.fsync(destination_handle.fileno())
        atomic_replace(temporary, destination)
        temporary = None
        sync_directory(destination.parent)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def create_rollback_backup(source: Path, backup: Path) -> None:
    """Create a recoverable same-directory backup before replacing *source*."""
    source = Path(source)
    backup = Path(backup)
    try:
        os.link(source, backup)
        sync_directory(backup.parent)
        return
    except OSError:
        backup.unlink(missing_ok=True)
    try:
        _copy_file_durably(source, backup)
    except Exception:
        backup.unlink(missing_ok=True)
        raise


def restore_rollback_backup(backup: Path, destination: Path) -> None:
    """Atomically restore *backup*, leaving it intact if replacement fails."""
    backup = Path(backup)
    destination = Path(destination)
    restore_candidate: Path | None = destination.with_name(
        f".{destination.name}.{secrets.token_hex(8)}.restore"
    )
    try:
        _copy_file_durably(backup, restore_candidate)
        atomic_replace(restore_candidate, destination)
        restore_candidate = None
        sync_directory(destination.parent)
    finally:
        if restore_candidate is not None:
            restore_candidate.unlink(missing_ok=True)
