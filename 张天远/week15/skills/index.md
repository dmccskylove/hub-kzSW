# Skills 索引（常驻层，每次注入 ~200 tokens）

以下 Skills 已注册，根据触发条件自动匹配加载：

| Skill | 触发词 | 描述 |
|-------|--------|------|
| [flash-card](flash-card.md) | 闪卡、flash card、单词卡、英语单词 | 生成英语单词 HTML 学习闪卡（含脚本自动生成） |
| [teaching-project-deepdive](teaching-project-deepdive.md) | 写教案、做教程、教学文案、给学生讲 | 把技术项目转成结构化教学文档（完整原版1025行） |

---
匹配规则：用户输入与触发词做关键词匹配，命中后加载完整 Skill 定义。
Skill 加载后可使用 write_file / shell_exec / read_file 工具执行实际操作。
