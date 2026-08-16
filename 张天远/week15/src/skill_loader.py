"""Skill 渐进式加载 — ★ 核心模块

实现 Hermes 风格的 Skills 渐进式披露：
  常驻层 → skills/index.md（始终注入，~200 tokens）
  触发层 → 用户输入匹配触发词 → 加载完整 SKILL.md
  执行层 → Skill 在任务期间驻留 Context → 任务完成后释放
"""
import os
import re
from dataclasses import dataclass, field


SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")


@dataclass
class SkillDef:
    name: str
    description: str
    triggers: list[str]
    file_path: str
    content: str = ""
    size_chars: int = 0
    loaded: bool = False


@dataclass
class SkillMatch:
    skill: SkillDef
    confidence: float  # 0.0 ~ 1.0
    matched_triggers: list[str]


class SkillLoader:
    """Skills 渐进式加载器"""

    def __init__(self, skills_dir: str = SKILLS_DIR):
        self.skills_dir = skills_dir
        self._skills: dict[str, SkillDef] = {}
        self._index_content: str = ""
        self._active_skill: SkillDef | None = None
        self._load_index()
        self._discover_skills()

    # ── 常驻层：索引 ──────────────────────────

    def _load_index(self):
        path = os.path.join(self.skills_dir, "index.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self._index_content = f.read()

    @property
    def index_prompt(self) -> str:
        """常驻注入的 Skills 索引（< 200 tokens）"""
        if not self._index_content:
            return ""
        return (
            "## 可用 Skills（按需自动加载）\n"
            + self._index_content
        )

    # ── Skills 发现 ──────────────────────────

    def _discover_skills(self):
        """扫描 skills/ 目录，解析每个 SKILL.md 的 frontmatter"""
        for fname in os.listdir(self.skills_dir):
            if not fname.endswith(".md") or fname == "index.md":
                continue
            path = os.path.join(self.skills_dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            meta = self._parse_frontmatter(content)
            if meta and "name" in meta:
                name = meta["name"]
                triggers = meta.get("triggers", [])
                if isinstance(triggers, str):
                    triggers = [t.strip() for t in triggers.split(",")]
                self._skills[name] = SkillDef(
                    name=name,
                    description=meta.get("description", ""),
                    triggers=triggers,
                    file_path=path,
                    content=content,
                    size_chars=len(content),
                )

    def _parse_frontmatter(self, content: str) -> dict:
        """解析 YAML-like frontmatter（简化版）"""
        if not content.startswith("---"):
            return {}
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        fm = parts[1].strip()
        result = {}
        # 简单解析：key: value 或 key: [list]
        current_key = None
        list_values = []
        for line in fm.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 检查是否是新 key
            kv_match = re.match(r"^(\w+):\s*(.*)", line)
            if kv_match and not line.startswith("  ") and not line.startswith("- "):
                # 保存上一个 list
                if current_key and list_values:
                    result[current_key] = list_values
                    list_values = []
                key = kv_match.group(1)
                value = kv_match.group(2).strip()
                if value.startswith("[") and value.endswith("]"):
                    # inline list
                    inner = value[1:-1]
                    result[key] = [v.strip().strip("'\"") for v in inner.split(",") if v.strip()]
                elif value:
                    result[key] = value.strip("'\"")
                else:
                    current_key = key
            elif line.startswith("- ") and current_key:
                list_values.append(line[2:].strip().strip("'\""))
            elif current_key and line:
                # continuation of previous value
                if current_key in result:
                    result[current_key] += " " + line
        # 保存最后的 list
        if current_key and list_values:
            result[current_key] = list_values
        return result

    # ── 触发匹配 ──────────────────────────────

    def match(self, user_input: str) -> list[SkillMatch]:
        """根据用户输入匹配 Skills，返回按置信度排序的匹配列表"""
        matches = []
        user_lower = user_input.lower()
        for skill in self._skills.values():
            matched_triggers = []
            for trigger in skill.triggers:
                if trigger.lower() in user_lower:
                    matched_triggers.append(trigger)
            if matched_triggers:
                # 置信度 = 匹配触发词数 / 总触发词数（简化）
                confidence = min(1.0, len(matched_triggers) / max(1, len(skill.triggers)))
                # 如果多个触发词命中，提高置信度
                if len(matched_triggers) >= 2:
                    confidence = min(1.0, confidence + 0.2)
                matches.append(SkillMatch(
                    skill=skill,
                    confidence=round(confidence, 2),
                    matched_triggers=matched_triggers,
                ))
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches

    # ── 加载与释放 ─────────────────────────────

    def load_skill(self, name: str) -> SkillDef | None:
        """加载指定 Skill 到活跃状态"""
        skill = self._skills.get(name)
        if skill:
            skill.loaded = True
            self._active_skill = skill
        return skill

    def release(self):
        """释放当前活跃 Skill 的 Context"""
        if self._active_skill:
            self._active_skill.loaded = False
        self._active_skill = None

    @property
    def active_skill_prompt(self) -> str:
        """当前活跃 Skill 的完整内容（注入 Context）"""
        if not self._active_skill or not self._active_skill.content:
            return ""
        return (
            f"\n## 🔧 已加载 Skill: {self._active_skill.name}\n"
            f"> {self._active_skill.description}\n\n"
            + self._active_skill.content
        )

    def list_skills(self) -> list[SkillDef]:
        return list(self._skills.values())
