#!/usr/bin/env python3
"""Plan or build three bounded independent source trees; never run git or a model."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
TASKS = ("recon2reason-bw-vllm", "robobrain-bw-vllm", "qwen3-asr-bw-vllm")
MAX_BYTES = 50 * 1024 * 1024
EXCLUDED_DIRS = {".git", "dist", "build", "runtime", "venv", "venvs", ".venv", "__pycache__", "node_modules", "models", "weights", ".pytest_cache"}
TEXT_SUFFIXES = {".py", ".sh", ".ps1", ".json", ".jsonl", ".md", ".txt", ".toml", ".yaml", ".yml", ".log", ".csv", ".tsv"}
SOURCE_SUFFIXES = TEXT_SUFFIXES - {".log"} | {".png", ".jpg", ".jpeg", ".svg"}
ASSET_SUFFIXES = SOURCE_SUFFIXES | {".log", ".wav", ".pdf", ".gif", ".webp"}
SECRET_SUFFIXES = {".key", ".pem", ".secret", ".token", ".pfx", ".p12", ".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".gguf", ".onnx"}
SECRET_NAMES = {"credentials.json", "secrets.json", "passwords.txt", ".netrc", ".npmrc", ".pypirc", "id_rsa", "id_ed25519"}
LINK = re.compile(r"\]\((?:<([^>]+)>|([^\s)]+))(?:\s+[\"'][^\n]*?[\"'])?\)")
REFERENCE_LINK = re.compile(r"^( {0,3}\[[^\]]+\]:\s*)(?:<([^>]+)>|(\S+))(.*)$")
CREDENTIAL_LITERAL = re.compile(rb"(?i)(?:[\"']?)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|client[_-]?secret)(?:[\"']?)\s*[:=]\s*[\"']([A-Za-z0-9_./+!@#$%^&*=-]{8,})[\"']")


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def relative_name(value):
    if not isinstance(value, str) or "\\" in value or ":" in value:
        raise ValueError("Source paths must be repository-relative POSIX paths")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("Source path traversal/absolute path is refused")
    return path.as_posix()


def safe_source(root, name):
    name = relative_name(name)
    current = root
    for part in PurePosixPath(name).parts:
        current = current / part
        if current.exists() or current.is_symlink():
            attrs = current.lstat()
            if current.is_symlink() or getattr(attrs, "st_file_attributes", 0) & 0x400:
                raise ValueError("Symlink/reparse source is refused: " + name)
    if not current.resolve().is_relative_to(root):
        raise ValueError("Source escaped workspace: " + name)
    return current


def forbidden_name(name):
    path = PurePosixPath(name)
    basename = path.name.lower()
    return (any(part.lower() in EXCLUDED_DIRS for part in path.parts)
            or basename == ".env" or basename.startswith(".env.")
            or basename in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES)


def scan_payload(name, payload):
    if forbidden_name(name):
        raise ValueError("Excluded runtime, credentials or weights source: " + name)
    if len(payload) > MAX_BYTES:
        raise ValueError("Single source exceeds 50 MiB: " + name)
    if PurePosixPath(name).suffix.lower() in TEXT_SUFFIXES or PurePosixPath(name).name == "METADATA":
        if re.search(rb"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----", payload) or CREDENTIAL_LITERAL.search(payload):
            raise ValueError("Possible embedded credential/private key; review before packaging: " + name)


def outside_fences(text, transform):
    result = []
    fence = None
    for line in text.splitlines(keepends=True):
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            result.append(line)
            if re.match(r"^ {0,3}" + re.escape(fence[0]) + "{" + str(fence[1]) + r",}\s*$", line):
                fence = None
        elif opening:
            fence = (opening.group(1)[0], len(opening.group(1)))
            result.append(line)
        else:
            result.append(transform(line))
    return "".join(result)


def local_target(root, markdown_name, target):
    if not target or target.startswith("#"):
        return None
    parsed = urlsplit(target)
    if parsed.scheme:
        if parsed.scheme.lower() in {"http", "https", "mailto", "codex", "app", "chatgpt-conversation"}:
            return None
        raise ValueError("Unsupported/absolute Markdown link: " + target)
    if parsed.netloc or parsed.path.startswith(("/", "\\")):
        raise ValueError("Absolute/network Markdown link is refused: " + target)
    path_text = unquote(parsed.path)
    if "\\" in path_text:
        raise ValueError("Backslash Markdown link is refused: " + target)
    candidate = root.joinpath(*PurePosixPath(markdown_name).parent.parts, path_text)
    normalized = Path(os.path.abspath(candidate))
    if not normalized.is_relative_to(root):
        raise ValueError("Markdown link escapes source workspace: " + target)
    name = normalized.relative_to(root).as_posix()
    safe_source(root, name)
    return name, ("?" + parsed.query if parsed.query else "") + ("#" + parsed.fragment if parsed.fragment else "")


def markdown_targets(text):
    found = []

    def collect(line):
        for match in LINK.finditer(line):
            found.append(match.group(1) or match.group(2))
        reference = REFERENCE_LINK.match(line)
        if reference:
            found.append(reference.group(2) or reference.group(3))
        return line

    outside_fences(text, collect)
    return found


def root_readme(root, task_name, payload):
    origin = f"tasks/{task_name}/README.md"

    def rebase(target):
        local = local_target(root, origin, target)
        if local is None:
            return target
        name, suffix = local
        return name + suffix

    def change(line):
        def inline(match):
            target = match.group(1) or match.group(2)
            rebased = rebase(target)
            return match.group(0).replace("<" + target + ">" if match.group(1) is not None else target,
                                          "<" + rebased + ">" if match.group(1) is not None else rebased, 1)
        line = LINK.sub(inline, line)
        reference = REFERENCE_LINK.match(line)
        if reference:
            target = reference.group(2) or reference.group(3)
            changed = rebase(target)
            ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            line = reference.group(1) + ("<" + changed + ">" if reference.group(2) is not None else changed) + reference.group(4) + ending
        return line

    text = outside_fences(payload.decode("utf-8"), change)
    title, separator, rest = text.partition("\n")
    notice = (f"\n本仓库唯一目标题为 `{task_name}`。当前为开发交付目录，正式就绪和赛事提交均未确认；"
              f"详见 [ROOT_TASK.json](ROOT_TASK.json)。`tasks/` 内其余两题仅保留为共享开发源码和测试依赖，"
              f"不作为本仓库提交目标。完整原报告保留于 [canonical README](tasks/{task_name}/README.md)。\n")
    return (title + separator + notice + rest).encode("utf-8")


class Sources:
    def __init__(self, root):
        self.root = root
        self.payloads = {}
        self.missing = set()

    def add(self, name, allow_asset=False):
        name = relative_name(name)
        path = safe_source(self.root, name)
        if forbidden_name(name):
            raise ValueError("Excluded source requested: " + name)
        if not path.is_file():
            self.missing.add(name)
            return
        if path.suffix.lower() not in (ASSET_SUFFIXES if allow_asset else SOURCE_SUFFIXES) and path.name not in {".gitignore", "METADATA"}:
            raise ValueError("Unapproved source file type: " + name)
        with path.open("rb") as source:
            payload = source.read(MAX_BYTES + 1)
        scan_payload(name, payload)
        total = sum(map(len, self.payloads.values())) - len(self.payloads.get(name, b"")) + len(payload)
        if total > MAX_BYTES:
            raise ValueError("Collected source exceeds 50 MiB")
        self.payloads[name] = payload

    def tree(self, folder, assets=False):
        base = safe_source(self.root, folder)
        if not base.is_dir():
            self.missing.add(folder)
            return
        for directory, dirs, files in os.walk(base, followlinks=False):
            for item in list(dirs):
                relative = (Path(directory) / item).relative_to(self.root).as_posix()
                safe_source(self.root, relative)
                if item.lower() in EXCLUDED_DIRS or item.endswith(".egg-info"):
                    dirs.remove(item)
            for item in sorted(files):
                relative = (Path(directory) / item).relative_to(self.root).as_posix()
                self.add(relative, assets)

    def collect_markdown_links(self):
        checked = set()
        while True:
            pending = [name for name in self.payloads if name.endswith(".md") and name not in checked]
            if not pending:
                return
            for name in pending:
                checked.add(name)
                for target in markdown_targets(self.payloads[name].decode("utf-8")):
                    local = local_target(self.root, name, target)
                    if local is None:
                        continue
                    dependency, _suffix = local
                    if dependency in self.payloads:
                        continue
                    if PurePosixPath(dependency).parts[0] not in {"evidence", "docs", "fixtures"}:
                        raise ValueError("Uncollected Markdown dependency outside evidence/docs/fixtures: " + dependency)
                    self.add(dependency, allow_asset=True)


def common_sources(root):
    sources = Sources(root)
    for name in ("pyproject.toml", ".gitignore"):
        sources.add(name)
    for folder in ("src", "scripts", "tests", "docs"):
        sources.tree(folder)
    # Keep all three small canonical source directories so shared tests remain runnable.
    # Evidence is the exact union of their explicit evidence_files and Markdown links.
    for task in TASKS:
        sources.tree("tasks/" + task)
        config_path = safe_source(root, f"tasks/{task}/task.json")
        if not config_path.is_file():
            continue
        config = json.loads(config_path.read_text(encoding="utf-8"))
        for name in config.get("evidence_files", []):
            if PurePosixPath(relative_name(name)).parts[0] not in {"evidence", "docs", "tasks", "fixtures"}:
                raise ValueError("Unapproved task evidence path: " + name)
            sources.add(name, allow_asset=True)
    sources.tree("fixtures", assets=True)
    sources.collect_markdown_links()
    return sources


def task_payloads(sources, task):
    files = dict(sources.payloads)
    # Keep evidence hashes and LF shell bytes stable even with core.autocrlf=true.
    files[".gitattributes"] = b"# Preserve source/evidence bytes across Git checkouts.\n* -text\n"
    readme = f"tasks/{task}/README.md"
    config = f"tasks/{task}/task.json"
    if readme not in files or config not in files:
        raise ValueError("Missing canonical target README/task.json: " + task)
    task_config = json.loads(files[config])
    files["README.md"] = root_readme(sources.root, task, files[readme])
    status = {"schema_version": 1, "primary_task": task, "canonical_task": config,
              "canonical_report": readme, "model": task_config.get("model", {}).get("id"),
              "track": task_config.get("track"), "framework": "vllm", "precision": "bf16",
              "source_task_status": task_config.get("status"), "formal_ready": False,
              "submitted": False, "repository_url": None,
              "image_reference": task_config.get("official", {}).get("image_reference"),
              "shared_task_sources_are_other_submission_targets": False,
              "notes": "Source/evidence snapshot only. No weights, model download, GPU run, git initialization, publication or official acceptance generated."}
    files["ROOT_TASK.json"] = (json.dumps(status, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    prefix = f"tasks/{task}/"
    for name in list(files):
        if name.startswith(prefix) and name.count("/") == 2 and name.endswith(".sh"):
            entry = PurePosixPath(name).name
            if entry == "env.sh":
                body = ("#!/usr/bin/env bash\n"
                        "_TASK_REPOSITORY_ROOT=\"$(cd -- \"$(dirname -- \"${BASH_SOURCE[0]}\")\" && pwd)\"\n"
                        f"source \"$_TASK_REPOSITORY_ROOT/tasks/{task}/env.sh\"\n"
                        "unset _TASK_REPOSITORY_ROOT\n")
            else:
                body = ("#!/usr/bin/env bash\nset -euo pipefail\n"
                        "REPOSITORY_ROOT=\"$(cd -- \"$(dirname -- \"${BASH_SOURCE[0]}\")\" && pwd)\"\n"
                        f"exec bash \"$REPOSITORY_ROOT/tasks/{task}/{entry}\" \"$@\"\n")
            files[entry] = body.encode("utf-8")
    total = sum(map(len, files.values()))
    if total > MAX_BYTES:
        raise ValueError(f"Repository source exceeds 50 MiB: {task} ({total} bytes)")
    return files, status


def plan(root, output, tasks=TASKS):
    for parent in (root, *root.parents):
        if parent.is_symlink() or (parent.exists() and getattr(parent.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("Source root cannot traverse a symlink/reparse path")
    root = root.resolve()
    if not output.is_absolute():
        raise ValueError("Output root must be absolute")
    if output.resolve() == root or root.is_relative_to(output.resolve()):
        raise ValueError("Output cannot contain/replace source workspace")
    sources = common_sources(root)
    prepared = {}
    for task in tasks:
        if task not in TASKS:
            raise ValueError("Unknown task slug: " + task)
        prepared[task] = task_payloads(sources, task)[0]
    return sources, prepared


def build(output, prepared, missing):
    if missing:
        raise ValueError("Required files missing; refusing build: " + ", ".join(sorted(missing)))
    # Validate every payload before mutating any destination, even for API callers.
    for task, files in prepared.items():
        if task not in TASKS:
            raise ValueError("Unknown task slug: " + task)
        if sum(map(len, files.values())) > MAX_BYTES:
            raise ValueError("Repository source exceeds 50 MiB: " + task)
        for name, payload in files.items():
            relative_name(name)
            scan_payload(name, payload)
    # Check every final destination before creating any of them.
    for task in prepared:
        destination = output / task
        if destination.exists() or destination.is_symlink():
            raise ValueError("Repository destination already exists: " + str(destination))
    for parent in (output, *output.parents):
        if parent.exists() and (parent.is_symlink() or getattr(parent.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("Output symlink/reparse parent is refused")
    results = []
    for task, files in prepared.items():
        destination = output / task
        destination.mkdir(parents=True, exist_ok=False)
        manifest = []
        for name, payload in sorted(files.items()):
            relative_name(name)
            scan_payload(name, payload)
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(payload)
            manifest.append({"path": name, "bytes": len(payload), "sha256": sha256(payload)})
        report = {"schema_version": 1, "primary_task": task, "formal_ready": False,
                  "submitted": False, "files": manifest,
                  "total_bytes": sum(item["bytes"] for item in manifest),
                  "manifest_scope": "All repository payload files except repository-manifest.json itself"}
        manifest_payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        with (destination / "repository-manifest.json").open("xb") as handle:
            handle.write(manifest_payload)
        results.append({"task": task, "path": str(destination), "files": len(manifest),
                        "bytes": report["total_bytes"], "manifest_sha256": sha256(manifest_payload)})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--output-root", type=Path, help="absolute parent; default SOURCE/dist/repositories")
    parser.add_argument("--task", choices=TASKS, action="append", help="select one or more; default all three")
    parser.add_argument("--build", action="store_true", help="explicitly write new independent source trees")
    args = parser.parse_args(argv)
    try:
        root = args.source_root.absolute()
        output = args.output_root or root / "dist/repositories"
        sources, prepared = plan(root, output, tuple(dict.fromkeys(args.task or TASKS)))
        report = {"mode": "build" if args.build else "plan_only", "source_root": str(root),
                  "output_root": str(output), "missing_required_files": sorted(sources.missing),
                  "formal_ready": False, "submitted": False, "git_commands_run": False,
                  "network_requests": 0, "model_loaded": False, "gpu_used": False}
        if args.build:
            report["repositories"] = build(output, prepared, sources.missing)
        else:
            report["repositories"] = [{"task": task, "path": str(output / task),
                                       "files": len(files), "bytes": sum(map(len, files.values()))}
                                      for task, files in prepared.items()]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2 if sources.missing else 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        print(json.dumps({"error": str(exc), "git_commands_run": False, "submitted": False}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
