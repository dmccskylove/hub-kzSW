# PPTX 文本提取：可靠方法

## 问题

`python-pptx` 依赖 `lxml`（C 扩展），在以下场景可能失败：
- `execute_code` 沙箱中 Python 版本与 conda 环境的 lxml 不兼容
- 系统缺 `lxml` 或版本冲突
- 跨平台部署时 C 扩展不可用

## 可靠方案：zipfile + ElementTree（纯标准库，零外部依赖）

PPTX 本质是 ZIP 文件，文本存储在 `ppt/slides/slideN.xml` 中。

```python
import zipfile, xml.etree.ElementTree as ET, re

pptx_path = "path/to/file.pptx"
with zipfile.ZipFile(pptx_path) as z:
    # 按 slide 编号排序
    slides = sorted(
        [n for n in z.namelist()
         if n.startswith('ppt/slides/slide') and n.endswith('.xml')],
        key=lambda x: int(re.search(r'slide(\d+)', x).group(1))
    )
    for s in slides:
        print(f'\n=== {s} ===')
        xml = z.read(s).decode('utf-8')
        root = ET.fromstring(xml)
        # 提取所有文本段落
        ns = 'http://schemas.openxmlformats.org/drawingml/2006/main'
        for p in root.iter(f'{{{ns}}}p'):
            line = ''.join(
                t.text or ''
                for t in p.iter(f'{{{ns}}}t')
            )
            if line.strip():
                print(line.strip())
```

## 使用方式

在终端直接运行（推荐）或写入 `.py` 文件后执行：

```bash
python -c "..." 2>&1 | head -400   # 截取前 400 行预览
python extract_pptx.py              # 完整提取到文件
```

## 局限性

- 不提取表格（表格在 `ppt/tables/` 下，需额外解析）
- 不保留格式（加粗、颜色等丢失）
- 文本顺序依赖 XML 元素顺序（一般从上到下，但复杂幻灯片可能不是）

## 适用场景

teaching-project-deepdive 的阶段 1 研究吸收——只需提取 PPT 文本内容用于教案编写时，此方法足够。
