"""Calculator 类的单元测试。

被测模块：calculator.Calculator（测试运行时 calculator.py 与该文件同目录）
覆盖点：
  - 四则运算各至少 1 个用例
  - 除法除零抛出 ValueError（消息含 '除数不能为0'）
  - history 追加的格式与顺序
  - clear_history 清空
  - get_last_result 返回值
  - 连续多次运算后 history 长度
"""

import unittest

from calculator import Calculator


class TestCalculator(unittest.TestCase):
    """Calculator 四则运算与状态管理测试。"""

    def setUp(self):
        self.calc = Calculator()

    # ---------- 初始状态 ----------
    def test_initial_state(self):
        """新建实例时 history 为空、last_result 为 None。"""
        self.assertEqual(self.calc.history, [])
        self.assertIsNone(self.calc.last_result)

    # ---------- 加法 ----------
    def test_add(self):
        """加法：2 + 3 = 5。"""
        result = self.calc.add(2, 3)
        self.assertEqual(result, 5)
        self.assertEqual(self.calc.last_result, 5)

    def test_add_negative_number(self):
        """加法：负数参与运算。"""
        result = self.calc.add(-1, 1)
        self.assertEqual(result, 0)

    # ---------- 减法 ----------
    def test_subtract(self):
        """减法：10 - 4 = 6。"""
        result = self.calc.subtract(10, 4)
        self.assertEqual(result, 6)
        self.assertEqual(self.calc.last_result, 6)

    def test_subtract_negative_result(self):
        """减法：结果为负数。"""
        result = self.calc.subtract(3, 8)
        self.assertEqual(result, -5)

    # ---------- 乘法 ----------
    def test_multiply(self):
        """乘法：4 * 6 = 24。"""
        result = self.calc.multiply(4, 6)
        self.assertEqual(result, 24)
        self.assertEqual(self.calc.last_result, 24)

    def test_multiply_by_zero(self):
        """乘法：乘以 0 结果为 0。"""
        result = self.calc.multiply(5, 0)
        self.assertEqual(result, 0)

    # ---------- 除法 ----------
    def test_divide(self):
        """除法：10 / 4 = 2.5。"""
        result = self.calc.divide(10, 4)
        self.assertEqual(result, 2.5)
        self.assertEqual(self.calc.last_result, 2.5)

    def test_divide_by_zero_raises_value_error(self):
        """除零必须抛出 ValueError 且消息含 '除数不能为0'。"""
        with self.assertRaises(ValueError) as ctx:
            self.calc.divide(10, 0)
        self.assertIn('除数不能为0', str(ctx.exception))

    # ---------- history 行为 ----------
    def test_history_format_and_order(self):
        """history 按运算顺序追加，且格式为 'a 运算符 b = 结果'。"""
        self.calc.add(2, 3)
        self.calc.subtract(10, 4)
        self.calc.multiply(4, 6)
        self.assertEqual(
            self.calc.history,
            ['2 + 3 = 5', '10 - 4 = 6', '4 * 6 = 24'],
        )

    def test_clear_history(self):
        """clear_history 清空 history。"""
        self.calc.add(2, 3)
        self.calc.multiply(4, 6)
        self.calc.clear_history()
        self.assertEqual(self.calc.history, [])

    def test_get_last_result(self):
        """get_last_result 返回最近一次运算结果。"""
        self.assertIsNone(self.calc.get_last_result())
        self.calc.add(2, 3)
        self.assertEqual(self.calc.get_last_result(), 5)
        self.calc.multiply(4, 6)
        self.assertEqual(self.calc.get_last_result(), 24)

    def test_history_length_after_multiple_operations(self):
        """连续多次运算后 history 长度等于运算次数。"""
        for i in range(5):
            self.calc.add(i, 1)
        self.assertEqual(len(self.calc.history), 5)


if __name__ == '__main__':
    unittest.main()
