import ast
import operator
import math
from hello_agents import ToolRegistry


def my_calculate(expression: str) -> str:
    """
    简单的数学计算函数
    """
    if not expression.strip():
        return "计算表达式不能为空"

    # 支持的基本运算
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

    # 支持的基本函数
    functions = {
        'sqrt': math.sqrt,
        'pi': math.pi,
    }

    try:
        node = ast.parse(expression, mode='eval')
        result = _eval_node(node.body, operators, functions)
        return str(result)
    except:
        return "计算失败，请检查表达式"


def _eval_node(node, operators, functions):
    """
    基于 AST（抽象语法树）的安全表达式求值器（内部递归函数）。
    通过遍历语法树节点，安全地计算数学表达式或调用白名单内的函数，
    从而替代危险的内置 eval() 函数。

    Args:
        node: 当前正在处理的 AST 节点。
        operators: 运算符映射字典，键为 AST 运算符类型（如 ast.Add），值为实际执行函数。
        functions: 函数白名单字典，键为允许的函数名（字符串），值为实际可调用对象。

    Returns:
        当前节点计算后的结果。
    """
    # 1. 处理常量节点（如数字 3.14、字符串等）
    # 直接返回其值，这是递归的基础终止条件之一
    if isinstance(node, ast.Constant):
        return node.value

    # 2. 处理二元运算节点（如 1 + 2, a * b）
    elif isinstance(node, ast.BinOp):
        # 递归计算左操作数和右操作数的值
        left = _eval_node(node.left, operators, functions)
        right = _eval_node(node.right, operators, functions)

        # 根据操作符类型（如 ast.Add）从映射字典中获取对应的执行函数
        op = operators.get(type(node.op))

        # 执行运算并返回结果
        return op(left, right)

    # 3. 处理函数调用节点（如 max(1, 2), sin(x)）
    elif isinstance(node, ast.Call):
        # 获取被调用函数的名称
        func_name = node.func.id

        # 核心安全机制：检查函数名是否在允许的白名单中
        if func_name in functions:
            # 递归计算所有传入的参数值
            args = [_eval_node(arg, operators, functions) for arg in node.args]

            # 调用白名单中的函数，解包参数并返回执行结果
            return functions[func_name](*args)
    # 4. 处理普通名称节点（如变量名 x，或无参函数引用 max）
    elif isinstance(node, ast.Name):
        if node.id in functions:
            return functions[node.id]


def create_calculator_registry():
    """
    创建包含计算器的工具注册表
    """
    registry = ToolRegistry()

    # 注册计算器函数
    registry.register_function(
        func=my_calculate,
        name="my_calculator",
        description="简单的数学计算工具，支持基本运算(+,-,*,/)和sqrt函数"
    )
    return registry
