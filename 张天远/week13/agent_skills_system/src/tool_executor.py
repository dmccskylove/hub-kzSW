"""工具执行器 — Function Call 实现

每个工具是一个 ToolDef：name + description + parameters schema + execute 函数。
"""
import os
import subprocess
import json
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict  # JSON Schema
    execute: Callable  # (params: dict) -> str


class ToolExecutor:
    def __init__(self, work_dir: str = "."):
        self.work_dir = work_dir
        self._tools: dict[str, ToolDef] = {}
        self._register_builtins()

    def _register_builtins(self):
        # ── write_file ──
        self.register(ToolDef(
            name="write_file",
            description="Write content to a file. Use for generating HTML, scripts, config files, etc.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to working directory"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
            execute=self._write_file,
        ))

        # ── read_file ──
        self.register(ToolDef(
            name="read_file",
            description="Read content of a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to working directory"},
                },
                "required": ["path"],
            },
            execute=self._read_file,
        ))

        # ── list_files ──
        self.register(ToolDef(
            name="list_files",
            description="List files and directories. Use this instead of shell ls/dir.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path (default: current dir)", "default": "."},
                    "pattern": {"type": "string", "description": "Optional glob pattern like *.py", "default": "*"},
                },
            },
            execute=self._list_files,
        ))

        # ── shell_exec ──
        self.register(ToolDef(
            name="shell_exec",
            description="Execute a shell command (limited: no interactive, no network servers)",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                },
                "required": ["command"],
            },
            execute=self._shell_exec,
        ))

    def register(self, tool: ToolDef):
        self._tools[tool.name] = tool

    def get_schemas(self) -> list[dict]:
        """返回 OpenAI 兼容的工具 schema 列表"""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def execute(self, name: str, params: dict) -> str:
        """执行指定工具，返回结果字符串"""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: unknown tool '{name}'"
        try:
            return tool.execute(params)
        except Exception as e:
            return f"Error executing {name}: {e}"

    # ── 内置工具实现 ──

    def _write_file(self, params: dict) -> str:
        path = os.path.join(self.work_dir, params["path"])
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(params["content"])
        size = len(params["content"])
        return f"File written: {params['path']} ({size} bytes)"

    def _read_file(self, params: dict) -> str:
        path = os.path.join(self.work_dir, params["path"])
        if not os.path.exists(path):
            return f"Error: file not found: {params['path']}"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 3000:
            content = content[:3000] + f"\n... (truncated, {len(content)} total bytes)"
        return content

    def _list_files(self, params: dict) -> str:
        import glob as glob_mod
        base = os.path.join(self.work_dir, params.get("path", "."))
        pattern = params.get("pattern", "*")
        search = os.path.join(base, pattern)
        results = glob_mod.glob(search, recursive=False)
        if not results:
            return f"No files matching {pattern} in {base}"

        lines = []
        for p in sorted(results)[:50]:
            rel = os.path.relpath(p, self.work_dir)
            info = ""
            if os.path.isdir(p):
                rel += "/"
            else:
                size = os.path.getsize(p)
                info = f" ({size} bytes)"
            lines.append(f"  {rel}{info}")
        header = f"{len(results)} items in {params.get('path', '.')}" + (" (first 50):" if len(results) > 50 else ":")
        return header + "\n" + "\n".join(lines)

    def _shell_exec(self, params: dict) -> str:
        cmd = params["command"]
        # 安全检查
        dangerous = ["rm -rf /", "format", "del /f", "shutdown", "reboot"]
        for d in dangerous:
            if d in cmd.lower():
                return f"Error: dangerous command rejected: '{d}'"
        try:
            # Windows: 用 PowerShell；否则用 bash
            if os.name == "nt":
                result = subprocess.run(
                    ["powershell", "-Command", cmd],
                    capture_output=True, text=True,
                    timeout=30, cwd=self.work_dir,
                )
            else:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=30, cwd=self.work_dir,
                )
            out = result.stdout.strip()
            err = result.stderr.strip()
            parts = []
            if out:
                parts.append(out[:2000])
            if err:
                parts.append(f"[stderr] {err[:500]}")
            return "\n".join(parts) if parts else f"Command completed (exit={result.returncode})"
        except subprocess.TimeoutExpired:
            return "Error: command timed out (30s)"
