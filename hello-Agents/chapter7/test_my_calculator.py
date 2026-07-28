# test_my_calculator.py
from dotenv import load_dotenv
from my_calculator_tool import create_calculator_registry
import os

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def test_calculator_tool():
    """测试自定义计算器工具"""

    # 创建包含计算器的注册表
    registry = create_calculator_registry()

    print("🧪 测试自定义计算器工具\n")

    # 简单测试用例
    test_cases = [
        "2 + 3",  # 基本加法
        "10 - 4",  # 基本减法
        "5 * 6",  # 基本乘法
        "15 / 3",  # 基本除法
        "sqrt(16)",  # 平方根
    ]

    for i, expression in enumerate(test_cases, 1):
        print(f"测试 {i}: {expression}")
        result = registry.execute_tool("my_calculator", expression)
        # 兼容不同版本：ToolResponse 对象用 .text 属性，str 直接用
        result_text = result.text if hasattr(result, 'text') else result
        print(f"结果: {result_text}\n")


def test_with_simple_agent():
    """测试与SimpleAgent的集成"""
    from hello_agents import HelloAgentsLLM

    # 创建LLM客户端
    llm = HelloAgentsLLM()

    # 创建包含计算器的注册表
    registry = create_calculator_registry()

    print("🤖 与SimpleAgent集成测试:")

    # 模拟SimpleAgent使用工具的场景
    user_question = "请帮我计算 sqrt(16) + 2 * 3"

    print(f"用户问题: {user_question}")

    # 使用工具计算
    calc_result = registry.execute_tool("my_calculator", "sqrt(16) + 2 * 3")
    # 兼容不同版本：ToolResponse 对象用 .text 属性，str 直接用
    calc_result_text = calc_result.text if hasattr(calc_result, 'text') else calc_result
    print(f"计算结果: {calc_result_text}")

    # 构建最终回答
    final_messages = [
        {"role": "user", "content": f"计算结果是 {calc_result_text}，请用自然语言回答用户的问题：{user_question}"}
    ]

    print("\n🎯 SimpleAgent的回答:")
    response = llm.think(final_messages)
    for chunk in response:
        print(chunk, end="", flush=True)
    print("\n")


if __name__ == "__main__":
    test_calculator_tool()
    test_with_simple_agent()
