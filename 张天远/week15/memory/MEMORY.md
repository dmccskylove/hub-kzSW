# MEMORY.md — 跨会话持久记忆

## 格式说明
每条记忆格式：
### [category] 标题
记录时间：YYYY-MM-DD HH:MM
详细内容

category: preference | fact | event | decision

---
（记忆条目由 Memory Flush 自动追加）


### [fact] 计算器项目已生成
记录时间：2026-08-16 10:13
Python 计算器项目包含 calculator.py、test_calculator.py、README.md，10个单元测试全部通过。

### [event] 修复 README 接口不一致
记录时间：2026-08-16 10:13
第二次请求时发现并行生成的 README 与实际代码接口不一致，已修正为与实际行为匹配。

### [event] 完成Python计算器项目
记录时间：2026-08-16 10:33
并行生成了 calculator.py、test_calculator.py、README.md，8个单元测试全部通过。

### [fact] 计算器项目功能
记录时间：2026-08-16 10:33
Calculator类支持四则运算与历史记录，除零抛ValueError；历史记录为字符串列表。

### [fact] README已修正
记录时间：2026-08-16 10:33
并行生成时README与代码不符，已按代码修正，并写入MEMORY.md。