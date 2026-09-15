#!/usr/bin/env python3
"""Extract an uploaded GEO input ZIP with strict traversal and resource guards."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from preflight_common import atomic_write_json, sha256_file, utc_now


MAX_FILES = 2000
MAX_TOTAL_UNCOMPRESSED = 2 * 1024 * 1024 * 1024
MAX_FILE_UNCOMPRESSED = 512 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1000


def safe_member_name(name: str) -> PurePosixPath:
    if "\x00" in name or "\\" in name:
        raise ValueError(f"Unsafe ZIP member name: {name!r}")
    member = PurePosixPath(name)
    if not member.parts or member.is_absolute() or any(part in {"", ".", ".."} for part in member.parts):
        raise ValueError(f"Unsafe ZIP member path: {name!r}")
    if member.parts and ":" in member.parts[0]:
        raise ValueError(f"Drive-qualified ZIP member path: {name!r}")
    return member


def extract(archive: Path, destination: Path) -> dict:
    archive = archive.resolve()
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not destination.is_dir() or any(destination.iterdir()):
            raise ValueError(f"ZIP destination must not already contain data: {destination}")
        destination.rmdir()
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent)).resolve()
    extracted = []
    seen = set()
    try:
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            if len(members) > MAX_FILES:
                raise ValueError(f"ZIP contains more than {MAX_FILES} entries")
            total = sum(item.file_size for item in members)
            if total > MAX_TOTAL_UNCOMPRESSED:
                raise ValueError("ZIP uncompressed size exceeds the configured limit")
            validated = []
            for info in members:
                member = safe_member_name(info.filename)
                casefolded = str(member).casefold()
                if casefolded in seen:
                    raise ValueError(f"Duplicate/case-colliding ZIP path: {info.filename!r}")
                seen.add(casefolded)
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ValueError(f"ZIP symlinks are forbidden: {info.filename!r}")
                if info.flag_bits & 0x1:
                    raise ValueError(f"Encrypted ZIP entries are forbidden: {info.filename!r}")
                if info.file_size > MAX_FILE_UNCOMPRESSED:
                    raise ValueError(f"ZIP member is too large: {info.filename!r}")
                ratio = info.file_size / max(1, info.compress_size)
                if ratio > MAX_COMPRESSION_RATIO:
                    raise ValueError(f"Suspicious ZIP compression ratio: {info.filename!r}")
                validated.append((info, member))
            for info, member in validated:
                target = (staging / Path(*member.parts)).resolve()
                if os.path.commonpath([staging, target]) != str(staging):
                    raise ValueError(f"ZIP member escapes destination: {info.filename!r}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(info, "r") as source, target.open("xb") as sink:
                    shutil.copyfileobj(source, sink, length=1024 * 1024)
                final_target = destination / Path(*member.parts)
                extracted.append({
                    "member": info.filename,
                    "path": str(final_target),
                    "byte_size": target.stat().st_size,
                    "sha256": sha256_file(target),
                })
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "package_type": "geo_secure_zip_extraction",
        "schema_version": 1,
        "archive_path": str(archive),
        "archive_sha256": sha256_file(archive),
        "destination": str(destination),
        "extracted_at": utc_now(),
        "file_count": len(extracted),
        "files": extracted,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = extract(args.archive, args.destination)
        atomic_write_json(args.manifest.resolve(), result)
        print(json.dumps({"status": "PASS", "file_count": result["file_count"], "manifest": str(args.manifest.resolve())}, sort_keys=True))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
