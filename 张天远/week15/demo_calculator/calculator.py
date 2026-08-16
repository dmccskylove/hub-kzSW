"""一个简单的命令行计算器模块。"""


class Calculator:
    """支持加减乘除运算并记录历史结果的计算器。"""

    def __init__(self):
        """初始化空历史记录与空的上次结果。"""
        self.history = []
        self.last_result = None

    def add(self, a, b):
        """返回 a + b，并记录历史。"""
        result = a + b
        self._record(a, '+', b, result)
        return result

    def subtract(self, a, b):
        """返回 a - b，并记录历史。"""
        result = a - b
        self._record(a, '-', b, result)
        return result

    def multiply(self, a, b):
        """返回 a * b，并记录历史。"""
        result = a * b
        self._record(a, '*', b, result)
        return result

    def divide(self, a, b):
        """返回 a / b，b 为 0 时抛出 ValueError。"""
        if b == 0:
            raise ValueError('除数不能为0')
        result = a / b
        self._record(a, '/', b, result)
        return result

    def _record(self, a, op, b, result):
        """更新 last_result 并向 history 追加格式化记录。"""
        self.last_result = result
        self.history.append(f'{a} {op} {b} = {result}')

    def clear_history(self):
        """清空历史记录列表。"""
        self.history.clear()

    def get_last_result(self):
        """返回最近一次运算的结果。"""
        return self.last_result


def main():
    """命令行交互循环：输入 '数字 运算符 数字' 进行运算。"""
    calc = Calculator()
    print('请输入表达式，格式为：数字 运算符 数字（如 2 + 3），输入 q 或 quit 退出。')
    while True:
        try:
            line = input('> ').strip()
        except EOFError:
            break
        if line.lower() in ('q', 'quit'):
            break
        parts = line.split()
        if len(parts) != 3:
            print('输入格式错误，请按 "数字 运算符 数字" 格式输入。')
            continue
        a_str, op, b_str = parts
        try:
            a = float(a_str)
            b = float(b_str)
        except ValueError:
            print('数字解析失败，请重新输入。')
            continue
        try:
            if op == '+':
                result = calc.add(a, b)
            elif op == '-':
                result = calc.subtract(a, b)
            elif op == '*':
                result = calc.multiply(a, b)
            elif op == '/':
                result = calc.divide(a, b)
            else:
                print('不支持的运算符，仅支持 + - * /。')
                continue
        except ValueError as exc:
            print(exc)
            continue
        print(f'结果: {result}')
    print('历史记录:')
    for record in calc.history:
        print(record)


if __name__ == '__main__':
    main()
