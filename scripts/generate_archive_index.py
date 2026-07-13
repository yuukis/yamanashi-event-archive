#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_EVENT_FIELDS = [
    "uid",
    "title",
    "event_url",
    "started_at",
    "ended_at",
    "updated_at",
    "open_status",
]

EVENT_DEFAULTS = {
    "event_id": None,
    "catch": None,
    "hash_tag": None,
    "limit": None,
    "accepted": None,
    "waiting": None,
    "owner_name": None,
    "place": None,
    "address": None,
    "group_key": None,
    "group_name": None,
    "group_url": None,
    "description": None,
    "lat": None,
    "lon": None,
}

COMMUNITY_DEFAULTS = {
    "id": None,
    "sub_title": None,
    "url": None,
    "description": None,
    "owner_text": None,
    "image_url": None,
    "website_url": None,
    "x_username": None,
    "facebook_url": None,
    "member_users_count": None,
    "ical_url": None,
}


class ArchiveError(ValueError):
    pass


def parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(item) for item in inner.split(",")]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_simple_yaml(text: str, path: Path) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            raise ArchiveError(f"{path}:{line_number}: expected key: value")

        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            raise ArchiveError(f"{path}:{line_number}: empty key")

        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ArchiveError(f"{path}:{line_number}: invalid indentation")

        parent = stack[-1][1]
        if raw_value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = parse_scalar(raw_value)

    return root


def split_front_matter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ArchiveError(f"{path}: missing YAML front matter")
    try:
        _, front_matter, body = text.split("---", 2)
    except ValueError as exc:
        raise ArchiveError(f"{path}: unterminated YAML front matter") from exc
    return parse_simple_yaml(front_matter, path), body.strip()


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def date_from_started_at(started_at: str, path: Path) -> str:
    match = re.match(r"^\d{4}-\d{2}-\d{2}", started_at)
    if not match:
        raise ArchiveError(f"{path}: started_at must begin with YYYY-MM-DD")
    return match.group(0)


def event_identity(path: Path, front_matter: dict[str, Any]) -> tuple[str, str, str]:
    group_key = str(front_matter.get("group_key") or path.parent.name)
    stem_match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-(\d{3,})", path.stem)
    if stem_match:
        return group_key, stem_match.group(1), stem_match.group(2)

    started_at = front_matter.get("started_at")
    serial = front_matter.get("serial")
    if not started_at or not serial:
        raise ArchiveError(
            f"{path}: filename must be YYYY-MM-DD-serial.md or front matter must "
            "include started_at and serial"
        )
    return group_key, date_from_started_at(str(started_at), path), str(serial).zfill(3)


def load_config(path: Path) -> dict[str, Any]:
    return parse_simple_yaml(path.read_text(encoding="utf-8"), path)


def git_output(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = result.stdout.strip()
    return value or None


def normalize_git_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url.removeprefix("git@github.com:")
    if url.startswith("https://github.com/") and url.endswith(".git"):
        url = url[:-4]
    return url


def build_source(repo_root: Path) -> dict[str, str]:
    repository = os.environ.get("GITHUB_REPOSITORY")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    remote_url = None if repository else normalize_git_url(
        git_output(["remote", "get-url", "origin"], repo_root)
    )

    name = repository.split("/", 1)[1] if repository and "/" in repository else None
    if name is None and remote_url:
        name = remote_url.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1]
    if name is None:
        raise ArchiveError("source.name could not be detected from GitHub Actions or git")

    url = f"{server_url}/{repository}" if repository else remote_url
    if url is None:
        raise ArchiveError("source.url could not be detected from GitHub Actions or git")

    ref = (
        os.environ.get("GITHUB_REF_NAME")
        or os.environ.get("GITHUB_HEAD_REF")
        or git_output(["branch", "--show-current"], repo_root)
        or git_output(["rev-parse", "--short", "HEAD"], repo_root)
    )
    if ref is None:
        raise ArchiveError("source.ref could not be detected from GitHub Actions or git")

    return {
        "type": "archive_index",
        "name": name,
        "url": normalize_git_url(url) or url,
        "ref": ref,
    }


def load_communities(directory: Path) -> list[dict[str, Any]]:
    communities = []
    for path in sorted(directory.glob("*.md")):
        front_matter, body = split_front_matter(path)
        item = {**COMMUNITY_DEFAULTS, **front_matter}
        item.setdefault("key", path.stem)
        if not item.get("key"):
            raise ArchiveError(f"{path}: key is required")
        if not item.get("title"):
            raise ArchiveError(f"{path}: title is required")
        if not item.get("description") and body:
            item["description"] = body
        communities.append(item)
    return sorted(communities, key=lambda item: item["key"])


def load_events(
    directory: Path,
    communities_by_key: dict[str, dict[str, Any]],
    source_key: str,
) -> list[dict[str, Any]]:
    events = []
    for path in sorted(directory.rglob("*.md")):
        front_matter, body = split_front_matter(path)
        group_key, event_date, serial = event_identity(path, front_matter)
        community = communities_by_key.get(group_key, {})

        item = {**EVENT_DEFAULTS, **front_matter}
        item["group_key"] = group_key
        item["uid"] = f"{group_key}-{event_date}-{serial}@{source_key}"
        if not item.get("description") and body:
            item["description"] = body
        if not item.get("group_name") and community:
            item["group_name"] = community.get("title")
        if not item.get("group_url") and community:
            item["group_url"] = community.get("url") or community.get("website_url")

        missing = [field for field in REQUIRED_EVENT_FIELDS if not item.get(field)]
        if missing:
            raise ArchiveError(f"{path}: missing required fields: {', '.join(missing)}")
        events.append(item)

    return sorted(events, key=lambda item: (item["started_at"], item["uid"]))


def build_index(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(args.config)
    generated_at = args.generated_at or iso_now()
    source = build_source(args.config.parent)
    source_key = source["name"]
    communities = load_communities(args.communities)
    communities_by_key = {item["key"]: item for item in communities}
    events = load_events(args.events, communities_by_key, source_key)
    return {
        "schema_version": str(config.get("schema_version", "1.0")),
        "generated_at": generated_at,
        "source": source,
        "communities": communities,
        "events": events,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate archive index JSON from Markdown front matter."
    )
    parser.add_argument("--config", type=Path, default=Path("archive.yaml"))
    parser.add_argument(
        "--communities", type=Path, default=Path("content/communities")
    )
    parser.add_argument("--events", type=Path, default=Path("content/events"))
    parser.add_argument("--output", type=Path, default=Path("public/index.json"))
    parser.add_argument("--generated-at")
    args = parser.parse_args()

    try:
        index = build_index(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"Wrote {args.output} "
            f"({len(index['communities'])} communities, {len(index['events'])} events)"
        )
        return 0
    except ArchiveError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
