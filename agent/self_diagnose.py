"""Self-diagnose: codebase integrity and health checks.

丰小虾自我修复能力的第一步 —— 能够检查自身源码的完整性和状态。
"""
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SelfHealthReport:
    version: str = "0.1.0"
    agent_root: str = ""
    git_commit: str = ""
    git_branch: str = ""
    git_clean: bool = True
    core_modules_ok: bool = True
    missing_core_modules: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "agent_root": self.agent_root,
            "git": {
                "commit": self.git_commit,
                "branch": self.git_branch,
                "clean": self.git_clean,
            },
            "core_modules": {
                "ok": self.core_modules_ok,
                "missing": self.missing_core_modules,
            },
            "warnings": self.warnings,
            "errors": self.errors,
        }


CORE_MODULES = [
    "conversation_loop.py",
    "prompt_builder.py",
    "system_prompt.py",
    "tool_executor.py",
    "tool_guardrails.py",
    "tool_dispatch_helpers.py",
    "context_compressor.py",
    "conversation_compression.py",
    "memory_manager.py",
    "error_classifier.py",
    "message_sanitization.py",
    "insights.py",
    "agent_runtime_helpers.py",
]


def diagnose(agent_root: Optional[str] = None) -> SelfHealthReport:
    """Run self-diagnosis and return a HealthReport."""
    report = SelfHealthReport()

    if agent_root:
        root = Path(agent_root)
    else:
        # 默认是仓库根目录（agent/的父目录）
        root = Path(__file__).parent.parent.resolve()

    report.agent_root = str(root)

    # Git status
    for cmd, attr in [
        (["git", "rev-parse", "HEAD"], "git_commit"),
        (["git", "rev-parse", "--abbrev-ref", "HEAD"], "git_branch"),
    ]:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5, cwd=root
            )
            if result.returncode == 0:
                val = result.stdout.strip()
                if attr == "git_commit":
                    val = val[:12]
                setattr(report, attr, val)
        except Exception:
            report.warnings.append(f"{attr} check failed")

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5, cwd=root,
        )
        if result.returncode == 0:
            report.git_clean = not result.stdout.strip()
            if not report.git_clean:
                dirty = len([l for l in result.stdout.split("\n") if l.strip()])
                report.warnings.append(f"{dirty} uncommitted change(s)")
    except Exception:
        pass

    # Core modules
    missing = []
    for mod in CORE_MODULES:
        mod_path = root / "agent" / mod
        if not mod_path.exists():
            missing.append(mod)
    if missing:
        report.core_modules_ok = False
        report.missing_core_modules = missing
        report.errors.append(f"missing: {missing}")

    return report


def diagnose_json(agent_root: Optional[str] = None) -> str:
    """Run self-diagnosis and return JSON."""
    return json.dumps(diagnose(agent_root).to_dict(), indent=2)
