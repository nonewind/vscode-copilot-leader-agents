#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_MODEL = "DeepSeek-V4-Flash (gcmp.deepseek)"
EXTENSION_ID = "vicanent.gcmp"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install VS Code Copilot Leader agents globally")
    parser.add_argument("--model", help="Exact worker model ID")
    parser.add_argument("--skip-extension", action="store_true", help="Do not install GCMP")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=check)


def code_cli() -> str:
    executable = shutil.which("code")
    if not executable:
        raise RuntimeError("VS Code 'code' command is not on PATH")
    return executable


def user_settings_files() -> list[Path]:
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        user_root = home / "Library/Application Support/Code/User"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA is not defined")
        user_root = Path(appdata) / "Code/User"
    else:
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        user_root = config_home / "Code/User"

    files = [user_root / "settings.json"]
    profiles = user_root / "profiles"
    if profiles.exists():
        files.extend(sorted(profiles.glob("*/settings.json")))
    return files


def strip_jsonc(text: str) -> str:
    output: list[str] = []
    i = 0
    in_string = False
    escape = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_string:
            output.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            output.append(ch)
            i += 1
            continue
        if ch == "/" and nxt == "/":
            i += 2
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        output.append(ch)
        i += 1
    cleaned = "".join(output)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def read_settings(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.read_text(encoding="utf-8", errors="ignore").strip():
        return {}
    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        value = json.loads(strip_jsonc(text))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Cannot parse VS Code settings: {path}: {exc}") from exc


def discover_model(settings_files: list[Path]) -> str:
    explicit = os.environ.get("COPILOT_WORKER_MODEL")
    if explicit:
        return explicit

    candidates: list[str] = []
    pattern = re.compile(r"[^\"'\s,]+deepseek[^\"'\s,]*v4[^\"'\s,]*flash[^\"'\s,]*", re.I)
    for path in settings_files:
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="ignore")
            candidates.extend(pattern.findall(text))

    extension_roots = [Path.home() / ".vscode/extensions"]
    if platform.system() == "Windows":
        extension_roots.append(Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".vscode/extensions")
    for ext_root in extension_roots:
        if not ext_root.exists():
            continue
        for ext in ext_root.glob("vicanent.gcmp-*"):
            for filename in ["package.json", "README.md", "README.zh-CN.md"]:
                path = ext / filename
                if path.exists():
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    candidates.extend(pattern.findall(text))

    normalized: list[str] = []
    for value in candidates:
        value = value.strip('"\'`')
        if value not in normalized:
            normalized.append(value)
    if CANONICAL_MODEL in normalized:
        return CANONICAL_MODEL
    return normalized[0] if len(normalized) == 1 else CANONICAL_MODEL


def ensure_supported_vscode(code: str) -> None:
    result = run([code, "--version"], check=False)
    first = result.stdout.splitlines()[0].strip() if result.stdout.splitlines() else ""
    match = re.match(r"(\d+)\.(\d+)", first)
    if not match:
        print("WARNING: Unable to determine VS Code version; continuing.")
        return
    version = (int(match.group(1)), int(match.group(2)))
    if version < (1, 128):
        raise RuntimeError(f"VS Code Stable 1.128+ is required; detected {first}")


def ensure_extension(code: str, dry_run: bool) -> None:
    result = run([code, "--list-extensions"], check=False)
    installed = {line.strip().lower() for line in result.stdout.splitlines()}
    if EXTENSION_ID in installed:
        return
    print(f"Installing extension {EXTENSION_ID}...")
    if not dry_run:
        run([code, "--install-extension", EXTENSION_ID])


def backup_item(source: Path, backup_root: Path, dry_run: bool) -> None:
    if not source.exists():
        return
    relative = Path(str(source).replace(":", "" ).lstrip("/\\"))
    target = backup_root / relative
    print(f"Backup: {source} -> {target}")
    if dry_run:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        shutil.copy2(source, target)


def render_agent(source: Path, target: Path, model: str, backup_root: Path, dry_run: bool) -> None:
    backup_item(target, backup_root, dry_run)
    content = source.read_text(encoding="utf-8").replace("{{WORKER_MODEL}}", model)
    print(f"Install agent: {target}")
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def copy_tree(source: Path, target: Path, backup_root: Path, dry_run: bool) -> None:
    backup_item(target, backup_root, dry_run)
    print(f"Install: {target}")
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)


def merge_profile_settings(path: Path, model: str, backup_root: Path, dry_run: bool) -> None:
    backup_item(path, backup_root, dry_run)
    settings = read_settings(path)
    settings.update({
        "chat.agent.enabled": True,
        "chat.subagents.allowInvocationsFromSubagents": False,
        "chat.useCustomAgentHooks": True,
        "chat.utilityModel": model,
        "chat.utilitySmallModel": model,
        "chat.exploreAgent.defaultModel": model,
        "chat.planAgent.defaultModel": model,
        "github.copilot.chat.askAgent.model": model,
        "github.copilot.chat.implementAgent.model": model,
        "github.copilot.chat.exploreAgent.model": model,
    })
    print(f"Update profile settings: {path}")
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if sys.version_info < (3, 9):
        raise RuntimeError("Python 3.9 or newer is required")

    code = code_cli()
    ensure_supported_vscode(code)
    if not args.skip_extension:
        ensure_extension(code, args.dry_run)

    settings_files = user_settings_files()
    model = args.model or discover_model(settings_files)
    print(f"Worker model: {model}")

    home = Path.home()
    copilot = home / ".copilot"
    agent_dir = copilot / "agents"
    skill_dir = copilot / "skills"
    hook_dir = copilot / "hooks"
    runtime_root = copilot / "vscode-copilot-leader-agents"
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = runtime_root / "backups" / timestamp

    agent_map = {
        "leader.agent.md": "leader.agent.md",
        "analyzer.agent.md": "leader-analyzer.agent.md",
        "implementer.agent.md": "leader-implementer.agent.md",
        "tester.agent.md": "leader-tester.agent.md",
        "reviewer.agent.md": "leader-reviewer.agent.md",
    }
    for source_name, target_name in agent_map.items():
        render_agent(REPO_ROOT / "src/agents" / source_name, agent_dir / target_name, model, backup_root, args.dry_run)

    for skill in sorted((REPO_ROOT / "src/skills").iterdir()):
        if skill.is_dir():
            copy_tree(skill, skill_dir / skill.name, backup_root, args.dry_run)

    guard_runtime = runtime_root / "hooks"
    if not args.dry_run:
        guard_runtime.mkdir(parents=True, exist_ok=True)
    for name in ["guard.py", "guard.ps1"]:
        source = REPO_ROOT / "src/hooks" / name
        target = guard_runtime / name
        backup_item(target, backup_root, args.dry_run)
        print(f"Install hook runtime: {target}")
        if not args.dry_run:
            shutil.copy2(source, target)
    hook_target = hook_dir / "vscode-copilot-leader-guard.json"
    backup_item(hook_target, backup_root, args.dry_run)
    print(f"Install hook config: {hook_target}")
    if not args.dry_run:
        hook_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / "src/hooks/vscode-copilot-leader-guard.json", hook_target)

    for settings_file in settings_files:
        merge_profile_settings(settings_file, model, backup_root, args.dry_run)

    state = {
        "version": (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "installed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "worker_model": model,
        "extension": EXTENSION_ID,
        "settings_files": [str(p) for p in settings_files],
        "backup_root": str(backup_root),
    }
    if not args.dry_run:
        runtime_root.mkdir(parents=True, exist_ok=True)
        (runtime_root / "install-state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validator = REPO_ROOT / "scripts/validate.py"
        result = subprocess.run([sys.executable, str(validator), "--installed"], text=True)
        if result.returncode != 0:
            raise RuntimeError("Installed configuration validation failed")

    print("\nInstallation complete.")
    print("Reload VS Code, open Copilot Chat, and select the 'Leader' custom agent.")
    print("Configure GCMP credentials manually; this installer does not read or store them.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
