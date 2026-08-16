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
    def __init__(self, work_dir: str = ".", dispatch_callback=None):
        self.work_dir = work_dir
        self._tools: dict[str, ToolDef] = {}
        self._register_builtins()
        if dispatch_callback:
            self._register_dispatch(dispatch_callback)

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
            description=(
                "Execute a shell command (limited: no interactive, no network servers). "
                "★ IMPORTANT: this machine runs Windows PowerShell 5.1 — use PowerShell syntax, "
                "e.g. Get-ChildItem / python script.py / python -m unittest test_x -v. "
                "NOT bash syntax (ls -la, grep, rm, find will fail). Deleting files is forbidden."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                },
                "required": ["command"],
            },
            execute=self._shell_exec,
        ))

    def _register_dispatch(self, dispatch_callback):
        """注册 dispatch_subagents 工具（仅主 agent 的 ToolExecutor 调用）"""
        self.register(ToolDef(
            name="dispatch_subagents",
            description=(
                "Dispatch multiple subagents to work in PARALLEL. Use when the user's task "
                "contains 2+ independent work items (e.g. writing multiple files, processing "
                "multiple topics/files). Input 'subtasks' is a JSON array of task descriptions, "
                "each must include goal, output path and key points. "
                "Example: [\"编写 calculator.py 实现四则运算\", \"编写 test_calculator.py 做单元测试\"]"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "subtasks": {"type": "string",
                                 "description": "JSON array of subtask descriptions, e.g. [\"task1\", \"task2\"]"},
                },
                "required": ["subtasks"],
            },
            execute=dispatch_callback,
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
        # 安全检查（★ Week15 加固：删除类命令全拦，防止 subagent 自主删除项目文件）
        dangerous = [
            "rm -rf", "rm -fr", "rm -r ", "rmdir /s", "rd /s", "del /s", "del /q",
            "remove-item", "rm -recurse", "del -r", "erase", "diskpart", "format",
            "shutdown", "reboot", "chkdsk /f", ">nul & del",
        ]
        cmd_lower = cmd.lower()
        for d in dangerous:
            if d in cmd_lower:
                return f"Error: dangerous command rejected: '{d}' (subagent 无权删除文件，如确需删除请让主管 agent 处理)"
        # 单文件 rm / del 也拦截（write_file 已可覆盖，无需删除）
        import re as _re
        if _re.search(r"(^|[;&|])\s*(rm|del|remove|erase)\s+", cmd_lower):
            return "Error: delete command rejected (subagent 无权删除文件，write_file 覆盖即可)"
        try:
            # Windows: 用 PowerShell；否则用 bash
            # ★ 编码：Windows PowerShell 输出为系统 ANSI(GBK)，用 errors=replace 防 UnicodeDecodeError 崩溃
            if os.name == "nt":
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", cmd],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=30, cwd=self.work_dir,
                )
            else:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
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
