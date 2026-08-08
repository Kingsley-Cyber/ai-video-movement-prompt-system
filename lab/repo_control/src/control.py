#!/usr/bin/env python3
"""Build and query the CPCS repository map, work queue, and implementation log."""

from __future__ import annotations

import argparse
import ast
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker


MAP_SCHEMA = "cpcs.repository_map/1.0"
EVENT_SCHEMA = "cpcs.implementation_event/1.0"
MAP_RELATIVE = Path("lab/repo_control/derived/repository_map.json")
LAYER_MAP_RELATIVE = Path("lab/repo_control/derived/REPOSITORY_LAYER_MAP.md")
EVENT_RELATIVE = Path("lab/repo_control/implementation_events.jsonl")
LOCK_RELATIVE = Path("work/repo_control/implementation_events.lock")
EXCLUDED_MAP_PATHS = {
    MAP_RELATIVE.as_posix(),
    LAYER_MAP_RELATIVE.as_posix(),
    EVENT_RELATIVE.as_posix(),
}
TERMINAL_EVENTS = {"completed", "abandoned"}
ALLOWED_TRANSITIONS = {
    None: {"admitted", "started"},
    "admitted": {"started", "blocked", "abandoned"},
    "started": {"checkpoint", "verification", "blocked", "completed", "abandoned"},
    "checkpoint": {"checkpoint", "verification", "blocked", "completed", "abandoned"},
    "verification": {"checkpoint", "verification", "blocked", "completed", "abandoned"},
    "blocked": {"started", "abandoned"},
    "completed": set(),
    "abandoned": set(),
}
STATUS_VALUES = {
    "WORKING", "PARTIAL", "TEST_ONLY", "PLACEHOLDER", "MISSING", "BLOCKED",
    "UNKNOWN", "SUPERSEDED",
}


class RepoControlError(ValueError):
    """Raised when repository-control inputs or derived state fail closed."""


def find_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "AGENTS.md").exists() and (candidate / "lab/registry.yaml").exists():
            return candidate
    raise RepoControlError("run from inside the CPCS repository")


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode()


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=False, capture_output=True, text=True,
    )
    if result.returncode:
        raise RepoControlError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def repository_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        raise RepoControlError(result.stderr.decode(errors="replace").strip())
    paths = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        path = raw.decode("utf-8")
        if path in EXCLUDED_MAP_PATHS or "__pycache__" in PurePosixPath(path).parts:
            continue
        paths.append(path)
    return sorted(set(paths))


def language_for(path: str) -> str | None:
    suffixes = {
        ".py": "python", ".json": "json", ".jsonl": "jsonl", ".yaml": "yaml",
        ".yml": "yaml", ".md": "markdown", ".xml": "xml", ".toml": "toml",
        ".js": "javascript", ".css": "css", ".html": "html", ".csv": "csv",
        ".tsv": "tsv", ".txt": "text",
    }
    return suffixes.get(PurePosixPath(path).suffix.lower())


def directory_nodes(files: Iterable[str]) -> set[str]:
    directories = {"."}
    for path in files:
        parent = PurePosixPath(path).parent
        while parent.as_posix() != ".":
            directories.add(parent.as_posix())
            parent = parent.parent
    return directories


def nearest_owner(root: Path, path: str) -> str:
    candidate = PurePosixPath(path)
    parent = candidate if (root / path).is_dir() else candidate.parent
    while parent.as_posix() != ".":
        owner = parent / "AGENTS.md"
        if (root / owner.as_posix()).exists():
            return owner.as_posix()
        parent = parent.parent
    return "AGENTS.md"


def split_markdown_table_row(line: str) -> list[str]:
    """Split one Markdown row without treating pipes inside code spans as separators."""
    cells: list[str] = []
    buffer: list[str] = []
    in_code = False
    escaped = False
    for character in line.strip():
        if character == "`" and not escaped:
            in_code = not in_code
            buffer.append(character)
        elif character == "|" and not in_code and not escaped:
            cells.append("".join(buffer).strip())
            buffer = []
        else:
            buffer.append(character)
        escaped = character == "\\" and not escaped
        if character != "\\":
            escaped = False
    cells.append("".join(buffer).strip())
    if cells and cells[0] == "":
        cells.pop(0)
    if cells and cells[-1] == "":
        cells.pop()
    return cells


def parse_requirements(root: Path) -> list[dict[str, Any]]:
    rows = []
    lines = (root / "ARCHITECTURE.md").read_text(encoding="utf-8").splitlines()
    for line in lines:
        if not re.match(r"^\| REQ-[0-9]{3} \|", line):
            continue
        columns = split_markdown_table_row(line)
        if len(columns) != 9:
            raise RepoControlError(
                f"architecture requirement row has {len(columns)} columns: {columns[0]}"
            )
        (
            requirement_id, requirement, expected, observed, status, impact,
            dependency, remediation, verifier,
        ) = columns
        if status not in STATUS_VALUES:
            raise RepoControlError(f"{requirement_id} has unknown status {status}")
        rows.append({
            "id": requirement_id,
            "requirement": requirement,
            "expected": expected,
            "observed": observed,
            "status": status,
            "impact": impact,
            "dependency_text": dependency,
            "dependencies": sorted(set(re.findall(r"REQ-[0-9]{3}", dependency))),
            "remediation": remediation,
            "verifier": verifier,
        })
    if not rows:
        raise RepoControlError("ARCHITECTURE.md contains no requirement rows")
    return rows


def module_index(files: Iterable[str]) -> tuple[dict[str, str], dict[str, str]]:
    module_to_path: dict[str, str] = {}
    path_to_module: dict[str, str] = {}
    for path in files:
        posix = PurePosixPath(path)
        if posix.suffix != ".py":
            continue
        parts = list(posix.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            continue
        module = ".".join(parts)
        module_to_path[module] = path
        path_to_module[path] = module
    return module_to_path, path_to_module


def imported_modules(path: Path, module: str) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return set()
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".") if package else []
                keep = max(0, len(parts) - (node.level - 1))
                prefix = ".".join(parts[:keep])
                base = ".".join(part for part in (prefix, base) if part)
            if base:
                imports.add(base)
                imports.update(
                    f"{base}.{alias.name}" for alias in node.names if alias.name != "*"
                )
    return imports


def resolve_module(name: str, module_to_path: dict[str, str]) -> str | None:
    current = name
    while current:
        if current in module_to_path:
            return module_to_path[current]
        current = current.rpartition(".")[0]
    return None


def build_repository_map(root: Path) -> dict[str, Any]:
    files = repository_files(root)
    directories = directory_nodes(files)
    nodes: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str, str]] = set()

    def add_node(node: dict[str, Any]) -> None:
        previous = nodes.get(node["id"])
        if previous is not None and previous != node:
            raise RepoControlError(f"repository-map node collision: {node['id']}")
        nodes[node["id"]] = node

    for directory in sorted(directories):
        node_id = f"dir:{directory}"
        add_node({
            "id": node_id,
            "type": "directory",
            "label": directory,
            "path": directory,
            "owner": nearest_owner(root, directory),
        })
        if directory != ".":
            parent = PurePosixPath(directory).parent.as_posix()
            edges.add((f"dir:{parent}", node_id, "contains"))

    owner_paths = sorted({nearest_owner(root, path) for path in files} | {"AGENTS.md"})
    for owner in owner_paths:
        add_node({
            "id": f"owner:{owner}",
            "type": "owner",
            "label": owner,
            "path": owner,
            "owner": owner,
        })

    for path in files:
        absolute = root / path
        owner = nearest_owner(root, path)
        add_node({
            "id": f"file:{path}",
            "type": "file",
            "label": PurePosixPath(path).name,
            "path": path,
            "owner": owner,
            "language": language_for(path),
            "content_sha256": file_hash(absolute),
        })
        parent = PurePosixPath(path).parent.as_posix()
        edges.add((f"dir:{parent}", f"file:{path}", "contains"))
        edges.add((f"file:{path}", f"owner:{owner}", "governed_by"))

    requirements = parse_requirements(root)
    path_nodes = {
        row["path"]: row["id"] for row in nodes.values() if row.get("path")
    }
    for row in requirements:
        add_node({
            "id": f"requirement:{row['id']}",
            "type": "requirement",
            "label": f"{row['id']} {row['requirement']}",
            "status": row["status"],
            "impact": row["impact"],
            "remediation": row["remediation"],
            "verifier": row["verifier"],
        })
        for dependency in row["dependencies"]:
            edges.add(
                (f"requirement:{row['id']}", f"requirement:{dependency}", "depends_on")
            )
        text = " ".join(
            (row["expected"], row["observed"], row["remediation"], row["verifier"])
        )
        for mention in re.findall(r"`([^`]+)`", text):
            clean = mention.split(":", 1)[0].rstrip("/")
            target = path_nodes.get(clean)
            if target:
                edges.add((f"requirement:{row['id']}", target, "mentions"))

    module_to_path, path_to_module = module_index(files)
    for path, module in sorted(path_to_module.items()):
        for imported in imported_modules(root / path, module):
            target = resolve_module(imported, module_to_path)
            if not target or target == path:
                continue
            edge_type = "tests" if "tests" in PurePosixPath(path).parts else "imports"
            edges.add((f"file:{path}", f"file:{target}", edge_type))

    edge_rows = [
        {"source": source, "target": target, "type": edge_type}
        for source, target, edge_type in sorted(
            edges, key=lambda row: (row[2], row[0], row[1])
        )
    ]
    node_rows = [nodes[node_id] for node_id in sorted(nodes)]
    return {
        "schema": MAP_SCHEMA,
        "generated_from": {
            "architecture_sha256": file_hash(root / "ARCHITECTURE.md"),
            "agent_contract_sha256": file_hash(root / "AGENTS.md"),
            "registry_sha256": file_hash(root / "lab/registry.yaml"),
        },
        "nodes": node_rows,
        "edges": edge_rows,
        "stats": {
            "directories": sum(row["type"] == "directory" for row in node_rows),
            "files": sum(row["type"] == "file" for row in node_rows),
            "owners": sum(row["type"] == "owner" for row in node_rows),
            "requirements": sum(row["type"] == "requirement" for row in node_rows),
            "edges": len(edge_rows),
        },
    }


def _directory_contract(root: Path) -> list[dict[str, str]]:
    try:
        document = ET.parse(root / "AGENTS.md")
    except (ET.ParseError, OSError) as exc:
        raise RepoControlError(f"cannot read root directory contract: {exc}") from exc
    rows = []
    for node in document.findall("./directory_contract/directory"):
        path = node.attrib.get("path", "").strip()
        purpose = " ".join("".join(node.itertext()).split())
        if not path or not purpose:
            raise RepoControlError("directory contract requires path and purpose")
        rows.append({"path": path, "purpose": purpose})
    if not rows:
        raise RepoControlError("root AGENTS.md contains no directory contract")
    return rows


def _markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _stable_ready_requirements(requirements: list[dict[str, Any]]) -> list[str]:
    by_id = {row["id"]: row for row in requirements}
    ready = []
    for row in requirements:
        if row["status"] in {"WORKING", "SUPERSEDED"}:
            continue
        blockers = [
            dependency
            for dependency in row["dependencies"]
            if dependency in by_id
            and by_id[dependency]["status"] not in {"WORKING", "SUPERSEDED"}
        ]
        if not blockers:
            ready.append(row["id"])
    return sorted(ready)


def render_repository_layer_map(root: Path, graph: dict[str, Any]) -> str:
    """Project the deterministic graph into a compact human repository guide."""
    file_nodes = [row for row in graph["nodes"] if row["type"] == "file"]
    owner_counts: dict[str, int] = defaultdict(int)
    for row in file_nodes:
        owner_counts[row["owner"]] += 1
    requirements = parse_requirements(root)
    status_counts: dict[str, int] = defaultdict(int)
    for row in requirements:
        status_counts[row["status"]] += 1
    ready = _stable_ready_requirements(requirements)
    stats = graph["stats"]
    lines = [
        "# CPCS Repository Layer Map",
        "",
        "> Generated by `python3 lab/repo_control/src/control.py rebuild`. Do not hand edit.",
        "",
        "This page answers where a concern lives and which file owns its rules. "
        "`ARCHITECTURE.md` remains implementation-state authority; this page is a disposable view.",
        "",
        "## Current map",
        "",
        f"- {stats['files']} mapped files across {stats['directories']} directories",
        f"- {stats['owners']} routed owner contracts",
        f"- {stats['requirements']} architecture requirements",
        f"- {stats['edges']} file, import, test, ownership, and requirement edges",
        "- Requirement states: "
        + ", ".join(f"{key}={status_counts[key]}" for key in sorted(status_counts)),
        "- Dependency-ready requirements: " + (", ".join(ready) if ready else "none"),
        "",
        "## Which authority answers which question",
        "",
        "| Question | Owner file |",
        "|---|---|",
        "| What is implemented, partial, missing, or blocked? | `ARCHITECTURE.md` |",
        "| What sequence and growth rules should future work follow? | `REPO_CONTINUITY_IMPLEMENTATION_PLAN.md` |",
        "| Which contract governs a task or directory? | nearest `AGENTS.md`, starting at root `AGENTS.md` |",
        "| Which active artifact or executable owns a capability? | `lab/registry.yaml` |",
        "| Which files, tests, imports, owners, and requirements are connected? | `lab/repo_control/derived/repository_map.json` |",
        "| What implementation work actually occurred? | `lab/repo_control/implementation_events.jsonl` |",
        "",
        "## Governed layers",
        "",
        "| Directory | Responsibility | Routed owner | Files in subtree |",
        "|---|---|---|---:|",
    ]
    for row in _directory_contract(root):
        declared = row["path"]
        normalized = "." if declared == "/" else declared.rstrip("/")
        owner = "AGENTS.md" if normalized == "." else nearest_owner(root, normalized)
        count = (
            len(file_nodes)
            if normalized == "."
            else sum(
                node["path"] == normalized
                or node["path"].startswith(normalized + "/")
                for node in file_nodes
            )
        )
        lines.append(
            f"| `{_markdown_cell(declared)}` | {_markdown_cell(row['purpose'])} | "
            f"`{_markdown_cell(owner)}` | {count} |"
        )
    lines.extend([
        "",
        "## Routed owners",
        "",
        "| Owner contract | Governed files |",
        "|---|---:|",
    ])
    for owner in sorted(owner_counts):
        lines.append(f"| `{_markdown_cell(owner)}` | {owner_counts[owner]} |")
    lines.extend([
        "",
        "## Main entrypoints",
        "",
        "| Need | Command or file |",
        "|---|---|",
        "| Use CPCS from a shell | `./bin/cpcs` |",
        "| Connect an MCP coding harness | `./bin/cpcs-mcp` |",
        "| Open the local graphical client | `cpcs-ui` |",
        "| Select dependency-ready work | `python3 lab/repo_control/src/control.py ready` |",
        "| Inspect a refactor neighborhood | `python3 lab/repo_control/src/control.py impact <path>` |",
        "| Rebuild this map and its JSON graph | `python3 lab/repo_control/src/control.py rebuild` |",
        "| Validate the complete repository | `python3 lab/scripts/validate_repo.py` |",
        "",
        "The JSON graph is the deeper machine view. Its `imports`, `tests`, `governed_by`, "
        "`depends_on`, and `mentions` edges support bounded impact inspection without changing source.",
        "",
    ])
    return "\n".join(lines)


def schema_validator(root: Path, name: str) -> Draft202012Validator:
    path = root / f"lab/repo_control/schemas/{name}.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_instance(root: Path, name: str, value: Any) -> None:
    errors = sorted(
        schema_validator(root, name).iter_errors(value), key=lambda error: list(error.path)
    )
    if errors:
        detail = "; ".join(
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise RepoControlError(f"{name}: {detail}")


def rebuild(root: Path) -> dict[str, Any]:
    value = build_repository_map(root)
    validate_instance(root, "repository_map", value)
    path = root / MAP_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, indent=1, sort_keys=True).encode() + b"\n")
    (root / LAYER_MAP_RELATIVE).write_text(
        render_repository_layer_map(root, value), encoding="utf-8"
    )
    return value


def read_events(root: Path, *, validate: bool = True) -> list[dict[str, Any]]:
    path = root / EVENT_RELATIVE
    if not path.exists():
        return []
    rows = []
    previous_hash = None
    states: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RepoControlError(f"implementation event line {line_number}: {exc}") from exc
        if validate:
            validate_instance(root, "implementation_event", row)
        if row["parent_event_hash"] != previous_hash:
            raise RepoControlError(
                f"implementation event line {line_number}: parent hash mismatch"
            )
        content = {key: value for key, value in row.items() if key != "event_hash"}
        expected_hash = sha256_bytes(canonical_bytes(content))
        if row["event_hash"] != expected_hash:
            raise RepoControlError(f"implementation event line {line_number}: event hash mismatch")
        prior = states.get(row["work_id"])
        if row["event_type"] not in ALLOWED_TRANSITIONS[prior]:
            raise RepoControlError(
                f"implementation event line {line_number}: invalid transition "
                f"{prior}->{row['event_type']}"
            )
        states[row["work_id"]] = row["event_type"]
        previous_hash = row["event_hash"]
        rows.append(row)
    return rows


def normalize_paths(paths: Iterable[str]) -> list[str]:
    output = []
    for raw in paths:
        path = PurePosixPath(raw)
        if path.is_absolute() or ".." in path.parts or path.as_posix() in ("", "."):
            raise RepoControlError(
                f"implementation-event path must be repository-relative: {raw}"
            )
        output.append(path.as_posix())
    return sorted(set(output))


def append_event(
    root: Path,
    *,
    work_id: str,
    requirement_id: str,
    event_type: str,
    actor: str,
    summary: str,
    files: Iterable[str] = (),
    verifications: list[dict[str, Any]] | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    if requirement_id not in {row["id"] for row in parse_requirements(root)}:
        raise RepoControlError(f"unknown architecture requirement {requirement_id}")
    lock_path = root / LOCK_RELATIVE
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        rows = read_events(root)
        last_for_work = next(
            (row for row in reversed(rows) if row["work_id"] == work_id), None
        )
        prior = last_for_work["event_type"] if last_for_work else None
        if event_type not in ALLOWED_TRANSITIONS[prior]:
            raise RepoControlError(f"invalid implementation transition {prior}->{event_type}")
        timestamp = occurred_at or datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
        body = {
            "schema": EVENT_SCHEMA,
            "work_id": work_id,
            "requirement_id": requirement_id,
            "event_type": event_type,
            "occurred_at": timestamp,
            "actor": actor,
            "summary": summary,
            "branch": run_git(root, "branch", "--show-current").strip() or "DETACHED",
            "revision": run_git(root, "rev-parse", "HEAD").strip(),
            "files": normalize_paths(files),
            "verifications": verifications or [],
            "parent_event_hash": rows[-1]["event_hash"] if rows else None,
        }
        event_id_hash = hashlib.sha256(canonical_bytes(body)).hexdigest()[:20]
        row = {"id": f"workevt_{event_id_hash}", **body}
        row["event_hash"] = sha256_bytes(canonical_bytes(row))
        validate_instance(root, "implementation_event", row)
        event_path = root / EVENT_RELATIVE
        event_path.parent.mkdir(parents=True, exist_ok=True)
        with event_path.open("a", encoding="utf-8") as stream:
            stream.write(canonical_bytes(row).decode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        return row


def check(root: Path) -> dict[str, Any]:
    built = build_repository_map(root)
    validate_instance(root, "repository_map", built)
    path = root / MAP_RELATIVE
    if not path.exists():
        raise RepoControlError("repository map is missing; run rebuild")
    stored = json.loads(path.read_text(encoding="utf-8"))
    validate_instance(root, "repository_map", stored)
    if canonical_bytes(stored) != canonical_bytes(built):
        raise RepoControlError("repository map is stale; run rebuild")
    layer_path = root / LAYER_MAP_RELATIVE
    if not layer_path.exists():
        raise RepoControlError("repository layer map is missing; run rebuild")
    expected_layer_map = render_repository_layer_map(root, built)
    if layer_path.read_text(encoding="utf-8") != expected_layer_map:
        raise RepoControlError("repository layer map is stale; run rebuild")
    events = read_events(root)
    node_ids = [row["id"] for row in stored["nodes"]]
    if len(node_ids) != len(set(node_ids)):
        raise RepoControlError("repository map contains duplicate node IDs")
    return {
        "status": "green",
        "map": stored["stats"],
        "layer_map": LAYER_MAP_RELATIVE.as_posix(),
        "implementation_events": len(events),
    }


def dirty_paths(root: Path) -> dict[str, str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        raise RepoControlError(result.stderr.decode(errors="replace").strip())
    output = {}
    entries = result.stdout.split(b"\0")
    index = 0
    while index < len(entries):
        raw = entries[index]
        index += 1
        if not raw:
            continue
        text = raw.decode("utf-8")
        status, path = text[:2], text[3:]
        if status[0] in "RC" and index < len(entries) and entries[index]:
            path = entries[index].decode("utf-8")
            index += 1
        output[path] = status
    return output


def impact(root: Path, target_path: str) -> dict[str, Any]:
    target = PurePosixPath(target_path).as_posix().rstrip("/") or "."
    graph = build_repository_map(root)
    node_ids = {row["id"] for row in graph["nodes"]}
    start = f"file:{target}" if f"file:{target}" in node_ids else f"dir:{target}"
    if start not in node_ids:
        raise RepoControlError(f"path is not mapped: {target_path}")
    outgoing: dict[str, list[tuple[str, str]]] = defaultdict(list)
    incoming: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for edge in graph["edges"]:
        outgoing[edge["source"]].append((edge["target"], edge["type"]))
        incoming[edge["target"]].append((edge["source"], edge["type"]))
    selected = {start}
    if start.startswith("dir:"):
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor, edge_type in outgoing[current]:
                if edge_type != "contains" or neighbor in selected:
                    continue
                selected.add(neighbor)
                if neighbor.startswith("dir:"):
                    queue.append(neighbor)
    seed_files = {node_id for node_id in selected if node_id.startswith("file:")}
    related_files = set(seed_files)
    for file_id in seed_files:
        for neighbor, edge_type in [*outgoing[file_id], *incoming[file_id]]:
            if edge_type in {"imports", "tests"} and neighbor.startswith("file:"):
                related_files.add(neighbor)
    selected.update(related_files)
    for file_id in related_files:
        for neighbor, edge_type in outgoing[file_id]:
            if edge_type == "governed_by":
                selected.add(neighbor)
        for neighbor, edge_type in incoming[file_id]:
            if edge_type == "mentions":
                selected.add(neighbor)
    dirty = dirty_paths(root)
    nodes = {row["id"]: row for row in graph["nodes"]}
    affected_files = sorted(
        row["path"]
        for node_id, row in nodes.items()
        if node_id in selected and row["type"] == "file"
    )
    requirements = sorted(
        row["label"]
        for node_id, row in nodes.items()
        if node_id in selected and row["type"] == "requirement"
    )
    owners = sorted({
        row["owner"]
        for node_id, row in nodes.items()
        if node_id in selected and row.get("owner")
    })
    return {
        "path": target,
        "owners": owners,
        "affected_files": affected_files,
        "requirements": requirements,
        "wip": {path: dirty[path] for path in affected_files if path in dirty},
    }


def ready_work(root: Path) -> dict[str, Any]:
    requirements = parse_requirements(root)
    by_id = {row["id"]: row for row in requirements}
    latest: dict[str, dict[str, Any]] = {}
    for event in read_events(root):
        latest[event["work_id"]] = event
    active_requirements = {
        event["requirement_id"]
        for event in latest.values()
        if event["event_type"] not in TERMINAL_EVENTS
    }
    ready = []
    blocked = []
    for row in requirements:
        if row["status"] in {"WORKING", "SUPERSEDED"}:
            continue
        blockers = [
            dependency
            for dependency in row["dependencies"]
            if dependency in by_id
            and by_id[dependency]["status"] not in {"WORKING", "SUPERSEDED"}
        ]
        item = {
            "id": row["id"],
            "requirement": row["requirement"],
            "status": row["status"],
            "blocked_by": blockers,
            "active": row["id"] in active_requirements,
            "remediation": row["remediation"],
            "verifier": row["verifier"],
        }
        (ready if not blockers else blocked).append(item)
    return {
        "ready": ready,
        "blocked": blocked,
        "active_work": list(latest.values()),
    }


def load_verifications(path: str | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise RepoControlError("verification file must contain a JSON array")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("rebuild")
    sub.add_parser("check")
    sub.add_parser("ready")
    impact_parser = sub.add_parser("impact")
    impact_parser.add_argument("path")
    log_parser = sub.add_parser("log")
    log_parser.add_argument("--work-id", required=True)
    log_parser.add_argument("--requirement", required=True)
    event_choices = sorted(set().union(*ALLOWED_TRANSITIONS.values()))
    log_parser.add_argument("--event", required=True, choices=event_choices)
    log_parser.add_argument("--actor", required=True)
    log_parser.add_argument("--summary", required=True)
    log_parser.add_argument("--file", action="append", default=[])
    log_parser.add_argument("--verification-file")
    args = parser.parse_args(argv)
    root = find_root()
    try:
        if args.command == "rebuild":
            value = rebuild(root)
        elif args.command == "check":
            value = check(root)
        elif args.command == "ready":
            value = ready_work(root)
        elif args.command == "impact":
            value = impact(root, args.path)
        else:
            value = append_event(
                root,
                work_id=args.work_id,
                requirement_id=args.requirement,
                event_type=args.event,
                actor=args.actor,
                summary=args.summary,
                files=args.file,
                verifications=load_verifications(args.verification_file),
            )
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    except RepoControlError as exc:
        print(f"REPO CONTROL RED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
