"""Markdown 记忆加载 — Layer 3 长期记忆"""
import os
from dataclasses import dataclass, field


MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory")


@dataclass
class MemoryContext:
    soul: str = ""
    user: str = ""
    memory: str = ""
    agents: str = ""
    total_chars: int = 0

    def assemble(self) -> str:
        parts = []
        if self.soul:
            parts.append(f"## Agent 人格\n{self.soul}")
        if self.agents:
            parts.append(f"## 操作规范\n{self.agents}")
        if self.user:
            parts.append(f"## 用户画像\n{self.user}")
        if self.memory:
            parts.append(f"## 长期记忆\n{self.memory}")
        return "\n\n".join(parts)


class MemoryLoader:
    def __init__(self, memory_dir: str = MEMORY_DIR):
        self.memory_dir = memory_dir

    def load_all(self) -> MemoryContext:
        ctx = MemoryContext()
        ctx.soul = self._read("SOUL.md")
        ctx.user = self._read("USER.md")
        ctx.memory = self._read("MEMORY.md")
        ctx.agents = self._read("AGENTS.md")
        ctx.total_chars = sum(len(v) for v in [ctx.soul, ctx.user, ctx.memory, ctx.agents])
        return ctx

    def _read(self, filename: str) -> str:
        path = os.path.join(self.memory_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return ""

    def write(self, filename: str, content: str):
        path = os.path.join(self.memory_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def append(self, filename: str, content: str):
        path = os.path.join(self.memory_dir, filename)
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n" + content)
