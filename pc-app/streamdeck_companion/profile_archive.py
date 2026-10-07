from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

ARCHIVE_FORMAT = "streamdeck-esp-profile"
ARCHIVE_VERSION = 1
MANIFEST_NAME = "manifest.json"
PROFILE_NAME = "profile.json"
ASSET_PREFIX = "assets/"


class ProfileArchiveError(ValueError):
    pass


def export_profile(
    profile: Mapping[str, Any],
    destination: str | Path,
    *,
    assets: Mapping[str, bytes] | None = None,
) -> Path:
    path = Path(destination)
    if path.suffix != ".streamdeck":
        path = path.with_suffix(".streamdeck")
    normalized = migrate_profile(profile)
    manifest = {
        "format": ARCHIVE_FORMAT,
        "version": ARCHIVE_VERSION,
        "profile_name": str(normalized.get("name") or "Profile"),
        "assets": sorted((assets or {}).keys()),
    }
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr(PROFILE_NAME, json.dumps(normalized, ensure_ascii=False, indent=2))
        for name, content in (assets or {}).items():
            safe_name = _safe_asset_name(name)
            archive.writestr(f"{ASSET_PREFIX}{safe_name}", content)
    return path


def import_profile(source: str | Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    try:
        with ZipFile(Path(source), "r") as archive:
            names = set(archive.namelist())
            if MANIFEST_NAME not in names or PROFILE_NAME not in names:
                raise ProfileArchiveError("archive is missing manifest.json or profile.json")
            manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
            _validate_manifest(manifest)
            profile = json.loads(archive.read(PROFILE_NAME).decode("utf-8"))
            if not isinstance(profile, dict):
                raise ProfileArchiveError("profile.json must contain an object")
            assets: dict[str, bytes] = {}
            for name in names:
                if not name.startswith(ASSET_PREFIX) or name.endswith("/"):
                    continue
                relative = name[len(ASSET_PREFIX) :]
                safe_name = _safe_asset_name(relative)
                assets[safe_name] = archive.read(name)
            return migrate_profile(profile), assets
    except (BadZipFile, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProfileArchiveError("invalid .streamdeck archive") from exc


def duplicate_profile(
    profile: Mapping[str, Any],
    *,
    existing_names: set[str] | None = None,
    requested_name: str | None = None,
) -> dict[str, Any]:
    """Create an independent profile copy with deterministic name collision handling."""
    clone = migrate_profile(profile)
    base = (requested_name or f"{clone['name']} - copie").strip()
    if not base:
        raise ProfileArchiveError("duplicated profile name cannot be empty")
    used = set(existing_names or ())
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base} ({suffix})"
        suffix += 1
    clone["name"] = candidate
    return clone


def migrate_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a shared profile to the current backward-compatible V2 shape.

    Migration stays intentionally additive: legacy root slots remain the home
    page while optional V2 collections are introduced only when absent. This
    keeps exports portable between installations without rewriting working
    historical configuration.
    """
    if not isinstance(profile, Mapping):
        raise ProfileArchiveError("profile must be an object")
    migrated = deepcopy(dict(profile))
    name = str(migrated.get("name") or "").strip()
    if not name:
        raise ProfileArchiveError("profile name cannot be empty")
    migrated["name"] = name
    migrated.setdefault("home_page_id", "home")
    migrated.setdefault("pages", [])
    migrated.setdefault("folders", [])
    migrated.setdefault("library", [])
    migrated.setdefault("encoders", [])
    migrated.setdefault("slots", [])
    for key in ("pages", "folders", "library", "encoders", "slots"):
        if not isinstance(migrated[key], list):
            raise ProfileArchiveError(f"profile field {key!r} must be a list")
    return migrated


def _validate_manifest(manifest: object) -> None:
    if not isinstance(manifest, dict):
        raise ProfileArchiveError("manifest must be an object")
    if manifest.get("format") != ARCHIVE_FORMAT:
        raise ProfileArchiveError("unsupported archive format")
    version = manifest.get("version")
    if not isinstance(version, int) or version <= 0:
        raise ProfileArchiveError("invalid archive version")
    if version > ARCHIVE_VERSION:
        raise ProfileArchiveError(f"unsupported archive version: {version!r}")


def _safe_asset_name(name: str) -> str:
    path = PurePosixPath(name.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ProfileArchiveError(f"unsafe asset path: {name!r}")
    normalized = str(path)
    if normalized in {".", ""}:
        raise ProfileArchiveError(f"unsafe asset path: {name!r}")
    return normalized
