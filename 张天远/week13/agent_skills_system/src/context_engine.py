"""Context 组装引擎 — 记忆 + Skills + 对话历史 → 完整 Context

每次 LLM 调用前，按以下顺序组装：
  1. SOUL.md（人格）
  2. AGENTS.md（操作规范）
  3. Skills 索引（常驻）+ 已加载 Skill（如触发）
  4. USER.md + MEMORY.md（长期记忆）
  5. 对话历史（Layer 2）
"""
from dataclasses import dataclass


@dataclass
class AssembledContext:
    system_prompt: str
    messages: list[dict]
    total_chars: int
    skills_loaded: list[str]
    skill_context_chars: int = 0


class ContextEngine:
    def __init__(self, memory_loader, skill_loader):
        self.memory_loader = memory_loader
        self.skill_loader = skill_loader

    def assemble(self, messages: list[dict]) -> AssembledContext:
        """组装完整 Context"""
        mem = self.memory_loader.load_all()

        # 1. 基础 System Prompt
        system_parts = [mem.assemble()]

        # 2. Skills 索引（常驻）
        index = self.skill_loader.index_prompt
        if index:
            system_parts.append(index)

        # 3. 已加载的活跃 Skill（触发层/执行层）
        active = self.skill_loader.active_skill_prompt
        skill_context_chars = 0
        skills_loaded = []
        if active:
            system_parts.append(active)
            skill_context_chars = len(active)
            if self.skill_loader._active_skill:
                skills_loaded.append(self.skill_loader._active_skill.name)

        system_prompt = "\n\n".join(system_parts)
        total_chars = len(system_prompt) + sum(len(m.get("content", "")) for m in messages)

        return AssembledContext(
            system_prompt=system_prompt,
            messages=messages,
            total_chars=total_chars,
            skills_loaded=skills_loaded,
            skill_context_chars=skill_context_chars,
        )
