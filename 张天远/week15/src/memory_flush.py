"""Memory Flush — 对话结束自动提取记忆

参考 Hermes 的做法：LLM 从对话中提取关键信息 → 写入 MEMORY.md / USER.md
"""
import json
import re
from .llm_config import chat
from .memory_loader import MemoryLoader


FLUSH_PROMPT_USER = """分析以下对话，提取用户信息，输出 JSON 数组。
每条格式：{{"field": "字段名", "value": "内容", "confidence": 0.0-1.0}}

字段可选：称呼、角色、偏好、技能、项目

对话：
{conversation}

只输出 JSON 数组，不要其他内容。如果没有可提取的信息，输出 []。"""

FLUSH_PROMPT_MEMORY = """分析以下对话，提取值得跨会话记住的信息，输出 JSON 数组。
每条格式：{{"category": "preference|fact|event|decision", "title": "简短标题", "content": "1-2句描述"}}

对话：
{conversation}

只输出 JSON 数组，不要其他内容。提取原则：
- preference: 用户偏好（"喜欢用 TypeScript"）
- fact: 事实信息（"项目在 M 盘"）
- event: 事件（"完成了文本分类项目"）
- decision: 决策（"决定使用 DeepSeek"）

最多提取 3 条。如果没有，输出 []。"""


class MemoryFlusher:
    def __init__(self):
        self.loader = MemoryLoader()

    def flush(self, messages: list[dict]) -> dict:
        """执行 Memory Flush，返回更新摘要"""
        conversation = "\n".join(
            f"[{m['role']}]: {m['content']}" for m in messages
        )
        result = {
            "user_updates": [],
            "memory_entries": [],
            "summary": "",
        }

        # Pass 1: 提取用户信息 → USER.md
        try:
            raw = chat([{"role": "user", "content": FLUSH_PROMPT_USER.format(conversation=conversation)}])
            user_json = self._extract_json(raw)
            if user_json:
                self._update_user(user_json)
                result["user_updates"] = [
                    f"{u.get('field', list(u.keys())[0])}: {u.get('value', list(u.values())[0])}"
                    for u in user_json if u
                ]
        except Exception as e:
            result["user_updates"] = [f"提取失败: {e}"]

        # Pass 2: 提取记忆条目 → MEMORY.md
        try:
            mem_json = self._extract_json(chat(
                [{"role": "user", "content": FLUSH_PROMPT_MEMORY.format(conversation=conversation)}]
            ))
            if mem_json:
                self._append_memory(mem_json)
                result["memory_entries"] = [
                    f"[{m.get('category', m.get('类型', 'fact'))}] {m.get('title', m.get('标题', ''))}"
                    for m in mem_json if m
                ]
        except Exception as e:
            result["memory_entries"] = [f"提取失败: {e}"]

        # Summary
        n_user = len(result["user_updates"])
        n_mem = len(result["memory_entries"])
        result["summary"] = f"Flush 完成: 用户画像 {n_user} 项, 记忆 {n_mem} 条"
        return result

    def _extract_json(self, text: str) -> list | None:
        """从 LLM 回复中提取 JSON，兼容数组和单对象"""
        # 去代码块包裹
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = text.strip()
        # 先尝试数组 [...]
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass
        # 回退单对象 {...}
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                return [result] if isinstance(result, dict) else result
            except json.JSONDecodeError:
                pass
        return None

    def _update_user(self, fields: list[dict]):
        """更新 USER.md — 兼容多种 LLM 输出格式"""
        current = self.loader._read("USER.md")
        new_lines = []
        for f in fields:
            # 兼容两种格式：
            #   A) {"field": "称呼", "value": "李四", "confidence": 0.9}
            #   B) {"称呼": "李四"} 等直接键值对
            if "field" in f and "value" in f:
                if f.get("confidence", 0.5) > 0.4:
                    new_lines.append(f"- {f['field']}: {f['value']}")
            else:
                # 提取所有非元数据键作为字段
                for k, v in f.items():
                    if k in ("confidence", "category", "title", "content"):
                        continue
                    if isinstance(v, str) and len(v) < 100:
                        new_lines.append(f"- {k}: {v}")
        if new_lines:
            if "## 偏好" not in current:
                current += "\n\n## 偏好\n（自动提取）\n"
            current += "\n" + "\n".join(new_lines)
            self.loader.write("USER.md", current)

    def _append_memory(self, entries: list[dict]):
        """追加记忆条目到 MEMORY.md — 兼容多种 LLM 输出格式"""
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = []
        for e in entries:
            # 兼容：
            #   A) {"category": "preference", "title": "...", "content": "..."}
            #   B) {"类型": "preference", "标题": "...", "内容": "..."}
            cat = e.get("category") or e.get("类型") or "fact"
            title = e.get("title") or e.get("标题") or ""
            content = e.get("content") or e.get("内容") or ""
            # 兜底：如果都没有，取第一个键值对
            if not title and not content:
                parts = [(k, v) for k, v in e.items()
                         if k not in ("category", "类型", "confidence")]
                if parts:
                    title = str(parts[0][0])
                    content = str(parts[0][1])
            if title or content:
                lines.append(f"\n### [{cat}] {title}")
                lines.append(f"记录时间：{ts}")
                lines.append(f"{content}")
        if lines:
            self.loader.append("MEMORY.md", "\n".join(lines))
