#!/usr/bin/env python3
"""Validate Iris plugin packaging invariants without contacting the MCP server."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NAME = "iris-calibration-operator"
VERSION = "1.0.0"
SERVER_ID = "iris"
ENDPOINT = "https://iris-ai-339343666693.us-central1.run.app/api/mcp"
PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"

REQUIRED_FILES = (
    "plugin.json",
    "mcp.json",
    ".mcp.json",
    ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    ".claude-plugin/marketplace.json",
    "skills/calibration-operator/SKILL.md",
    "skills/calibration-operator/agents/openai.yaml",
    "README.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "LICENSE",
)

TOKEN_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{20,})"),
    "service API token": re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
}

SENSITIVE_CONFIG_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "headers",
    "password",
    "refresh_token",
    "secret",
    "token",
}

errors: list[str] = []


def reject(message: str) -> None:
    errors.append(message)


def load_json(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        reject(f"{relative_path}: invalid or unreadable JSON ({exc})")
        return {}
    if not isinstance(value, dict):
        reject(f"{relative_path}: root value must be an object")
        return {}
    return value


def expect_identity(relative_path: str, payload: dict[str, Any]) -> None:
    if payload.get("name") != NAME:
        reject(f"{relative_path}: name must be {NAME!r}")
    if payload.get("version") != VERSION:
        reject(f"{relative_path}: version must be {VERSION!r}")
    if payload.get("license") != "Apache-2.0":
        reject(f"{relative_path}: license must be 'Apache-2.0'")


def expect_server(
    relative_path: str,
    payload: dict[str, Any],
    allowed_transports: set[str],
) -> None:
    servers = payload.get("mcpServers")
    if not isinstance(servers, dict) or set(servers) != {SERVER_ID}:
        reject(f"{relative_path}: mcpServers must contain only {SERVER_ID!r}")
        return
    server = servers.get(SERVER_ID)
    if not isinstance(server, dict):
        reject(f"{relative_path}: {SERVER_ID!r} server must be an object")
        return
    if server.get("type") not in allowed_transports:
        allowed = ", ".join(sorted(allowed_transports))
        reject(f"{relative_path}: server transport must be one of {allowed}")
    if server.get("url") != ENDPOINT:
        reject(f"{relative_path}: server URL does not match the canonical endpoint")
    if "headers" in server:
        reject(f"{relative_path}: headers must not be embedded in the package")


def inspect_sensitive_keys(value: Any, relative_path: str, pointer: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.casefold().replace("-", "_")
            if normalized in SENSITIVE_CONFIG_KEYS:
                reject(f"{relative_path}: sensitive field {pointer}.{key} is not allowed")
            inspect_sensitive_keys(child, relative_path, f"{pointer}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            inspect_sensitive_keys(child, relative_path, f"{pointer}[{index}]")


def package_files() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        return [
            path
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(ROOT).parts
        ]

    files: list[Path] = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        candidate = ROOT / raw_path.decode("utf-8")
        if candidate.is_file():
            files.append(candidate)
    return files


def scan_token_like_values() -> None:
    for path in package_files():
        try:
            if path.stat().st_size > 2_000_000:
                continue
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(ROOT).as_posix()
        for label, pattern in TOKEN_PATTERNS.items():
            if pattern.search(content):
                reject(f"{relative}: detected a token-like {label}")


def validate() -> None:
    for relative_path in REQUIRED_FILES:
        if not (ROOT / relative_path).is_file():
            reject(f"missing required file: {relative_path}")

    for path in ROOT.rglob("*"):
        relative_parts = path.relative_to(ROOT).parts
        if ".git" in relative_parts:
            continue
        if path.is_symlink():
            reject(f"symlink is not allowed in the package: {path.relative_to(ROOT)}")

    skill_files = sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("SKILL.md")
        if ".git" not in path.relative_to(ROOT).parts
    )
    if skill_files != ["skills/calibration-operator/SKILL.md"]:
        reject("the package must contain exactly one canonical calibration-operator SKILL.md")

    portable_manifest = load_json("plugin.json")
    portable_mcp = load_json("mcp.json")
    native_manifest = load_json(".codex-plugin/plugin.json")
    claude_manifest = load_json(".claude-plugin/plugin.json")
    native_mcp = load_json(".mcp.json")
    marketplace = load_json(".agents/plugins/marketplace.json")
    claude_marketplace = load_json(".claude-plugin/marketplace.json")

    expect_identity("plugin.json", portable_manifest)
    expect_identity(".codex-plugin/plugin.json", native_manifest)
    expect_identity(".claude-plugin/plugin.json", claude_manifest)

    if portable_manifest.get("$schema") != PLUGIN_SCHEMA:
        reject("plugin.json: unexpected Agent Plugins schema URL")
    if portable_mcp.get("$schema") != MCP_SCHEMA:
        reject("mcp.json: unexpected Agent Plugins MCP schema URL")

    expect_server("mcp.json", portable_mcp, {"streamable-http"})
    expect_server(".mcp.json", native_mcp, {"http", "streamable-http"})

    if native_manifest.get("skills") != "./skills/":
        reject(".codex-plugin/plugin.json: skills must point to './skills/'")
    if native_manifest.get("mcpServers") != "./.mcp.json":
        reject(".codex-plugin/plugin.json: mcpServers must point to './.mcp.json'")

    entries = marketplace.get("plugins")
    if marketplace.get("name") != "phoenix-calibration" or not isinstance(entries, list) or len(entries) != 1:
        reject(".agents/plugins/marketplace.json: expected one Phoenix Calibration plugin entry")
    else:
        entry = entries[0]
        source = entry.get("source") if isinstance(entry, dict) else None
        if not isinstance(entry, dict) or entry.get("name") != NAME:
            reject(".agents/plugins/marketplace.json: plugin name mismatch")
        if source != {"source": "local", "path": "./"}:
            reject(".agents/plugins/marketplace.json: plugin source must be the repository root")
        if entry.get("policy") != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}:
            reject(".agents/plugins/marketplace.json: unexpected installation policy")

    claude_entries = claude_marketplace.get("plugins")
    if claude_marketplace.get("name") != "phoenix-calibration" or not isinstance(claude_entries, list) or len(claude_entries) != 1:
        reject(".claude-plugin/marketplace.json: expected one Phoenix Calibration plugin entry")
    else:
        entry = claude_entries[0]
        if not isinstance(entry, dict) or entry.get("name") != NAME or entry.get("source") != ".":
            reject(".claude-plugin/marketplace.json: plugin must point to the repository root")

    skill_text = (ROOT / "skills/calibration-operator/SKILL.md").read_text(encoding="utf-8")
    required_skill_lines = (
        "name: calibration-operator",
        "license: Apache-2.0",
        '  author: "Phoenix Calibration"',
        f'  version: "{VERSION}"',
    )
    for line in required_skill_lines:
        if line not in skill_text:
            reject(f"skills/calibration-operator/SKILL.md: missing metadata line {line!r}")

    agent_text = (ROOT / "skills/calibration-operator/agents/openai.yaml").read_text(encoding="utf-8")
    required_agent_lines = (
        '      value: "iris"',
        '      transport: "streamable_http"',
        f'      url: "{ENDPOINT}"',
    )
    for line in required_agent_lines:
        if line not in agent_text:
            reject(f"skills/calibration-operator/agents/openai.yaml: missing dependency line {line!r}")
    if agent_text.count(ENDPOINT) != 1:
        reject("skills/calibration-operator/agents/openai.yaml: endpoint must be declared exactly once")

    for relative_path, payload in (
        ("plugin.json", portable_manifest),
        ("mcp.json", portable_mcp),
        (".mcp.json", native_mcp),
        (".codex-plugin/plugin.json", native_manifest),
        (".claude-plugin/plugin.json", claude_manifest),
        (".agents/plugins/marketplace.json", marketplace),
        (".claude-plugin/marketplace.json", claude_marketplace),
    ):
        inspect_sensitive_keys(payload, relative_path)

    scan_token_like_values()


validate()
if errors:
    print("Package validation failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("Package validation passed")
print(f"- identity: {NAME} {VERSION}")
print(f"- server: {SERVER_ID} -> {ENDPOINT}")
print("- skill copies: 1")
print("- embedded credential fields: none")
