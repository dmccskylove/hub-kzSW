# Depth Upgrade Execution Pattern (标准版 → 深度版)

The session that produced Week08 文本匹配深度版教案 established a reliable 5-step upgrade workflow. This reference captures the execution pattern.

## Trigger

User says "升级到深度版" or "能更详细一些吗" after receiving a 标准版 teaching document.

## Five Insertions (targeted ctx_edit, NOT full rewrite)

### 1. Mermaid Architecture Diagram
- **Insert after**: file-phase mapping table, before key numbers section
- **Content**: `graph TD` showing all script dependencies, with ★新/📎 markers on nodes
- **Size**: ~25 lines

### 2. Experiment Panorama
- **Insert with**: Mermaid diagram (same insertion point)
- **Content**: ASCII diagram showing experiments × datasets × paradigms matrix
- **Purpose**: "一张图看清全部覆盖" — students need the big picture before diving into details

### 3. Terminal Output Walkthrough
- **Insert as**: 全流程实操手册 section (before 附录A)
- **Structure**: 阶段0→5, each step labeled ✅ with:
  - Exact command
  - `# 预期输出：` or `# 预期看到：` comment block
  - `# 判断成功：` — how to know it worked (NOT just "it ran without error")
- **Key pattern**: Every training command MUST show what the student will see on screen. Students panic when they see loss=0.4812 and think it's broken — the walkthrough tells them "this is normal, here's what success looks like"

### 4. Multiple Analogies per Core Concept
- **Insert after**: existing analogy in each core concept section
- **Pattern**: "换个角度理解" or "换个场景" to introduce second angle
- **Rule**: second analogy MUST come from a different domain than the first
  - Example: BiEncoder §5 — first analogy "图书馆条形码", second "翻译/语义ID"
  - Example: CrossEncoder §6 — first analogy "同张纸上逐字比对", second "高考阅读理解并排看"
- **Also add** 💡 first-person narrative ("我第一次学的时候...") for the most confusing concepts

### 5. Version Bump
- Footer: v2.0 → v3.0（深度版）
- Table of Contents: add 全流程实操手册 entry

## Execution Notes

- **DO NOT rewrite the entire file**. Each insertion is 1 `ctx_edit` call.
- **Read context** before each insertion (行号漂移 after earlier insertions)
- **Order matters**: do the early-section insertions first (Mermaid, panorama), then later sections (实操手册). Earlier insertions change line numbers for later ones
- **Check duplication**: after inserting, search for any stale references to old experiment counts

## Pitfalls

| Pitfall | Avoidance |
|---------|-----------|
| ctx_edit on Windows paths with Chinese fails silently | Use `execute_code` + Python file I/O as fallback for large Chinese text replacements |
| Mermaid `[[...]]` nodes containing `→` arrow character | Parse error. Use `[...]` shape with `<br/>` for multi-line labels instead |
| Forgetting to update Table of Contents | Check after all insertions |

## Result Quality Check

After upgrade, the document should have:
- [ ] First-page visible Mermaid diagram AND panorama
- [ ] Every training command accompanied by expected terminal output
- [ ] Core concepts explained with ≥2 analogies from different domains
- [ ] 全流程实操手册 with 阶段0-5, each step having 判断成功 criteria
- [ ] Version bumped to v3.0（深度版）
