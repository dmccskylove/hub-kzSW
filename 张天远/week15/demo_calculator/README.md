# Python 计算器（Calculator）

一个简洁的 Python 命令行计算器项目，提供核心计算模块 `Calculator` 类、交互式命令行界面以及配套的单元测试。

## 项目简介

本项目实现了一个支持加（+）、减（-）、乘（*）、除（/）四则运算的计算器，包含以下部分：

- **calculator.py**：核心模块，定义 `Calculator` 类，提供四则运算方法、历史记录管理与最近结果查询，同时支持 `python calculator.py` 启动交互式命令行。
- **test_calculator.py**：单元测试模块，包含 13 个测试用例，覆盖四则运算、除零异常、历史记录、清空历史与最近结果查询等行为。
- **README.md**：本文档，介绍项目结构、接口用法与测试方法。

## 目录结构

```
calculator_project/
├── calculator.py          # 核心模块：Calculator 类 + 命令行入口
├── test_calculator.py     # 单元测试（13 个用例）
└── README.md              # 项目说明文档（本文档）
```

## Calculator 类接口说明

| 方法 | 说明 | 返回 | 异常 |
| --- | --- | --- | --- |
| `add(a, b)` | 计算 `a + b`，并记录一条形如 `'a + b = 结果'` 的历史 | 两数之和 | 无 |
| `subtract(a, b)` | 计算 `a - b`，并记录一条形如 `'a - b = 结果'` 的历史 | 两数之差 | 无 |
| `multiply(a, b)` | 计算 `a * b`，并记录一条形如 `'a * b = 结果'` 的历史 | 两数之积 | 无 |
| `divide(a, b)` | 计算 `a / b`，并记录一条形如 `'a / b = 结果'` 的历史 | 两数之商 | 当 `b == 0` 时抛出 `ValueError('除数不能为0')` |
| `clear_history()` | 清空全部历史记录 | `None` | 无 |
| `get_last_result()` | 返回最近一次运算的结果（无运算记录时返回 `None`） | 最近一次运算结果 | 无 |
| `history`（属性） | 字符串列表，保存每次运算的历史记录，格式为 `'2 + 3 = 5'`（运算符与等号两侧均带空格） | `list[str]` | 无 |

### 使用示例（Python 代码）

```python
from calculator import Calculator

calc = Calculator()
print(calc.add(2, 3))       # 5
print(calc.subtract(10, 4)) # 6
print(calc.multiply(3, 4))  # 12
print(calc.divide(8, 2))    # 4.0

print(calc.history)
# ['2 + 3 = 5', '10 - 4 = 6', '3 * 4 = 12', '8 / 2 = 4.0']

print(calc.get_last_result())  # 4.0
calc.clear_history()
print(calc.history)            # []

try:
    calc.divide(1, 0)
except ValueError as e:
    print(e)  # 除数不能为0
```

## 命令行用法

在项目目录下运行：

```bash
python calculator.py
```

启动交互式循环后，按 `数字 运算符 数字` 的格式输入表达式（数字与运算符之间用空格分隔），支持运算符 `+ - * /`。输入 `q` 或 `quit` 退出程序，并打印全部历史记录。

### 一次完整对话示例

```
$ python calculator.py
请输入表达式，格式为：数字 运算符 数字（如 2 + 3），输入 q 或 quit 退出。
> 2 + 3
结果: 5.0
> 10 - 4
结果: 6.0
> 3 * 4
结果: 12.0
> 8 / 2
结果: 4.0
> 1 / 0
除数不能为0
> q
历史记录:
2.0 + 3.0 = 5.0
10.0 - 4.0 = 6.0
3.0 * 4.0 = 12.0
8.0 / 2.0 = 4.0
```

## 测试运行方法

在项目目录下执行以下命令运行单元测试：

```bash
python -m unittest test_calculator -v
```

该命令以详细模式（verbose）运行 `test_calculator.py` 中的全部 13 个用例，覆盖四则运算、除零异常、历史记录格式、清空历史与最近结果查询等功能，全部通过时输出类似：

```
Ran 13 tests in 0.00s

OK
```

## License

本项目基于 MIT License 开源，您可以自由使用、修改与分发。
