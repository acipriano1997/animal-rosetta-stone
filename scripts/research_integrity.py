#!/usr/bin/env python3
"""Read-only byte inventory/verification. Private receipts confer no scientific or reuse rights."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

CONTRACT = "ARS-LOCAL-BYTE-INVENTORY-v1"


def fingerprint(path: Path) -> dict:
    """Reject symlinks, special files, replacement and writes during hashing."""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("NOT_REGULAR_FILE")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError("REPLACED_BEFORE_READ")
        h = hashlib.sha256()
        count = 0
        while block := stream.read(1024 * 1024):
            count += len(block)
            h.update(block)
        after = os.fstat(stream.fileno())
    final = path.lstat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if identity(before) != identity(after) or identity(after) != identity(final) or count != after.st_size:
        raise ValueError("CHANGED_DURING_READ")
    return {"size_bytes": count, "sha256": h.hexdigest()}


def safe_path(root: Path, relative: str) -> Path:
    p = PurePosixPath(relative)
    if not relative or p.is_absolute() or ".." in p.parts or p.as_posix() != relative or "\\" in relative:
        raise ValueError("UNSAFE_RELATIVE_PATH")
    path = root
    for part in p.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("SYMLINK_IN_SOURCE_PATH")
    return path


def inventory(root: Path) -> dict:
    files, errors = [], []
    def walk_error(error):
        errors.append({"path": str(Path(error.filename).relative_to(root)), "error": type(error).__name__})
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        dirs.sort()
        for name in dirs[:]:
            p = Path(directory) / name
            if p.is_symlink():
                errors.append({"path": p.relative_to(root).as_posix(), "error": "SYMLINK_DIRECTORY"})
                dirs.remove(name)
        for name in sorted(names):
            p = Path(directory) / name
            rel = p.relative_to(root).as_posix()
            try:
                files.append({"path": rel, **fingerprint(safe_path(root, rel))})
            except (OSError, ValueError) as error:
                errors.append({"path": rel, "error": str(error) if isinstance(error, ValueError) else type(error).__name__})
    groups = defaultdict(list)
    for record in files:
        groups[(record["size_bytes"], record["sha256"])].append(record["path"])
    return {"contract": CONTRACT, "status": "PASS" if not errors else "HELD",
            "scope": "LOCAL_BYTES_ONLY_NOT_PROVIDER_IDENTITY_OR_CAPTURE_TIME",
            "scientific_effect": "NONE", "redistribution_permission": "UNASSESSED",
            "files": files, "errors": errors,
            "byte_identical_groups": [v for v in groups.values() if len(v) > 1]}


def verify(root: Path, manifest: dict) -> dict:
    if manifest.get("contract") != CONTRACT or manifest.get("status") != "PASS" or manifest.get("errors") != []:
        raise ValueError("INCOMPLETE_OR_UNKNOWN_INVENTORY")
    records = manifest.get("files")
    if not isinstance(records, list):
        raise ValueError("INVALID_FILES")
    seen = set()
    # Validate the whole untrusted manifest before reading any referenced bytes.
    for r in records:
        if not isinstance(r, dict) or set(r) != {"path", "size_bytes", "sha256"}:
            raise ValueError("INVALID_RECORD")
        if not isinstance(r["path"], str) or r["path"] in seen:
            raise ValueError("DUPLICATE_OR_INVALID_PATH")
        safe_path(root, r["path"])
        seen.add(r["path"])
        if type(r["size_bytes"]) is not int or r["size_bytes"] < 0 or not isinstance(r["sha256"], str) or not re.fullmatch("[0-9a-f]{64}", r["sha256"]):
            raise ValueError("INVALID_FINGERPRINT")
    current = inventory(root)
    actual = {r["path"]: r for r in current["files"]}
    expected = {r["path"]: r for r in records}
    changed = sorted(p for p in expected.keys() & actual.keys() if expected[p] != actual[p])
    missing, extra = sorted(expected.keys() - actual.keys()), sorted(actual.keys() - expected.keys())
    return {"contract": CONTRACT, "status": "PASS" if not (changed or missing or extra or current["errors"]) else "HELD",
            "scientific_effect": "NONE", "changed": changed, "missing": missing, "extra": extra,
            "errors": current["errors"], "checked_files": len(actual)}


def write_private(path: Path, payload: dict) -> None:
    """Exclusive destination; an interrupted write remains conspicuously incomplete."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["inventory", "verify"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.root.is_symlink() or not args.root.is_dir():
            raise ValueError("ROOT_MUST_BE_REAL_DIRECTORY")
        root = args.root.resolve()
        if args.out.resolve().is_relative_to(root):
            raise ValueError("REPORT_MUST_BE_OUTSIDE_SOURCE_ROOT")
        if args.mode == "verify":
            if not args.manifest:
                raise ValueError("MANIFEST_REQUIRED")
            result = verify(root, json.loads(args.manifest.read_text()))
        else:
            result = inventory(root)
        write_private(args.out, result)
        print(json.dumps({"status": result["status"], "report": str(args.out)}))
        return 0 if result["status"] == "PASS" else 2
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"status": "HELD", "error": str(error) if isinstance(error, ValueError) else type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
