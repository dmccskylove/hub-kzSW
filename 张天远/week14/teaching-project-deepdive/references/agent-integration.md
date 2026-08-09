# 在 Agent 系统中使用本 Skill

## 核心反模式：不要用 ReAct 逐文件探索

**问题**：将本 skill 加载到 Agent 后，LLM 会进入 ReAct 循环逐文件读取，10+ 轮后 context 膨胀、超时崩溃。

**根因**：Hermes 使用本 skill 时，CodeGraph + lean-ctx 已将项目结构装入 context。LLM 拿到的是"已理解的项目"而非"需要探索的未知项目"。ReAct 逐文件读取是低效替代，不是等价方案。

## 正确做法：预加载上下文

触发本 skill 后、ReAct 循环启动前，自动注入到 System Prompt：

1. **PROJECT.md**（如存在）—— 最浓缩的知识源
2. **项目目录结构** —— 静态替代 list_files
3. **核心源文件列表** —— 让 LLM 知道有哪些模块

示例实现：

```python
def _preload_project_context(project_root: str) -> str:
    parts = []
    project_md = os.path.join(project_root, "PROJECT.md")
    if os.path.exists(project_md):
        with open(project_md) as f:
            parts.append(f.read()[:8000])
    dirs = [d for d in os.listdir(project_root) 
            if os.path.isdir(os.path.join(project_root, d))]
    parts.append("## 项目目录\n" + "\n".join(f"  {d}/" for d in dirs))
    return "\n\n".join(parts)
```

然后在 System Prompt 末尾追加：

```
## 预加载的项目上下文（已包含项目结构和核心文档，无需再读取）
{preloaded_context}

**重要：上下文已预加载完毕。立即开始写教案，用 write_file 直接输出。
不要再用 read_file 或 list_files 探索项目。**
```

## 关键约束

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| MAX_REACT_TURNS | 12-15 | 预加载后不需要太多轮 |
| 探索轮次上限 | ≤5 | 在 AGENTS.md 中明确约束 |
| Context 保护阈值 | 60,000 chars | 超阈值自动裁剪旧工具结果 |

## 环境适配

- **shell_exec**：Windows 下用 `powershell -Command`，不用 `cmd.exe /c`
- **list_files**：优先纯 Python 实现（glob），避免 `ls`/`dir` 跨平台问题

## Python `.format()` 花括号陷阱

Prompt 中的 JSON 示例必须双花括号转义：

```python
# ❌ 错误——{field}被 .format() 当成占位符
FLUSH_PROMPT = """
输出 JSON：{"field": "字段名", "value": "内容"}
对话：{conversation}
"""

# ✅ 正确——双花括号 {{field}} 输出为字面 {field}
FLUSH_PROMPT = """
输出 JSON：{{"field": "字段名", "value": "内容"}}
对话：{conversation}
"""
```

`f-string` 同样需要双花括号。任何含 JSON 示例的模板字符串都要检查。
