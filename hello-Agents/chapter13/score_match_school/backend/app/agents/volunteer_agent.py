"""志愿填报 Agent - 薄入口（编排层）

职责：
1. 初始化 LangChain Agent（LLM + 工具 + system_prompt）
2. 编排调用链：invoke → 提取输出 → JSON解析 → 省份过滤 → 返回
3. 单例入口 get_volunteer_agent()

不负责：
- ❌ 常量/枚举（在 constants.py）
- ❌ Prompt 模板/填充（在 prompt_loader.py）
- ❌ JSON 提取、省份校验、降级方案（在 parsers.py）
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun

from ..models.schemas import VolunteerPlan, VolunteerRequest
from .constants import DEFAULT_DISCLAIMER
from .prompt_loader import build_human_prompt, build_system_prompt
from .parsers import (
    build_fallback_plan,
    deduplicate_across_tiers,
    extract_json,
    filter_schools_by_province,
    plan_from_dict,
)


# ======================================================================
# LLM 构建
# ======================================================================

def _get_llm() -> ChatOpenAI:
    """构建 LangChain ChatOpenAI 实例（复用 .env 配置）"""
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
    model = os.getenv("LLM_MODEL_ID") or os.getenv("OPENAI_MODEL") or "qwen-max"

    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0.2,
        max_tokens=8192,
    )


# ======================================================================
# 工具构建
# ======================================================================

def _build_tools() -> List:
    """构建 LangChain 工具列表（DuckDuckGo 免费联网搜索）"""
    tools: List = []

    try:
        search = DuckDuckGoSearchRun()
        search.name = "web_search"
        search.description = (
            "联网搜索实时信息，包括历年高考分数线、学校招生计划、"
            "省份投档线等。支持中文搜索，从 DuckDuckGo 和百度等搜索引擎获取结果。"
            "搜索时务必包含具体年份和省份，例如：'2024年山西理科投档线'"
        )
        tools.append(search)
        print("✅ 已注册 DuckDuckGo 联网搜索工具（免费，无需API Key）")
    except Exception as e:
        print(f"⚠️  DuckDuckGo 搜索工具加载失败: {e}")

    return tools


# ======================================================================
# Agent 类
# ======================================================================

class VolunteerAgent:
    """LangChain 志愿填报 Agent（编排层）

    依赖注入：
    - llm      : ChatOpenAI
    - tools    : [DuckDuckGoSearchRun, ...]
    - prompt   : 从 prompt_loader 动态构建

    处理流水线（generate）：
        build_human_prompt → agent.invoke → extract_final_output
        → extract_json → json.loads → plan_from_dict
        → filter_schools_by_province → 返回 VolunteerPlan
    """

    def __init__(self):
        self._agent = None
        self._initialized = False

    # ---------- 初始化 ----------

    def initialize(
        self,
        llm: Optional[ChatOpenAI] = None,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
    ):
        """初始化 LangChain create_agent

        :param llm:           可选传入（测试时注入 mock LLM）
        :param tools:         可选传入（测试时注入 mock tools）
        :param system_prompt: 可选传入（测试时覆盖 prompt）
        """
        if self._initialized:
            return

        print("🔧 [VolunteerAgent] 初始化 LangChain Agent...")

        self._agent = create_agent(
            model=llm or _get_llm(),
            tools=tools or _build_tools(),
            system_prompt=system_prompt,  # 可传 None：由 generate() 在 invoke 时动态注入 system message
        )

        self._initialized = True
        print(f"✅ [VolunteerAgent] 初始化完成 (工具数={len(tools or _build_tools())})")

    # ---------- 生成方案 ----------

    def generate(self, request: VolunteerRequest) -> VolunteerPlan:
        """主入口：生成志愿方案"""
        if not self._initialized:
            self.initialize()

        # 构建 system_prompt（注入 create_agent 的方式是 invoke 时动态传 system message）
        current_year = datetime.now().year
        years_str = f"{current_year - 1},{current_year - 2},{current_year - 3}"
        system_prompt = build_system_prompt(
            province=request.province,
            score=request.score,
            subject_category=request.subject_category,
            target_major=request.target_major,
            years_str=years_str,
        )

        human_prompt = build_human_prompt(
            province=request.province,
            score=request.score,
            subject_category=request.subject_category,
            target_major=request.target_major,
        )

        self._print_start_log(request)

        # 调用 LangChain Agent
        try:
            result = self._invoke_with_system(system_prompt, human_prompt)
            output = self._extract_final_output(result)
            print(f"📥 [Agent] 原始输出长度: {len(output)}")
        except Exception as e:
            print(f"❌ [Agent] 调用失败: {e}")
            import traceback
            traceback.print_exc()
            return build_fallback_plan(request)

        # 解析 JSON → plan
        plan = self._parse_output_to_plan(output, request)
        return plan

    # ---------- 内部调用（system prompt 动态注入） ----------

    def _invoke_with_system(self, system_prompt: str, human_prompt: str) -> Dict:
        """LangChain 1.x create_agent 的 system_prompt 是初始化时传入的；
        但我们希望 system_prompt 随请求动态变化，所以用 system message 形式拼接。"""
        messages = [
            ("system", system_prompt),
            ("user", human_prompt),
        ]
        return self._agent.invoke({"messages": messages})

    # ---------- 结果提取 ----------

    @staticmethod
    def _extract_final_output(result: Dict) -> str:
        """从 LangChain agent 返回的 dict 中提取最后一个 AIMessage.content"""
        messages = result.get("messages", [])
        for msg in reversed(messages):
            content = getattr(msg, "content", None)
            if content and isinstance(content, str):
                return content
        return str(result)

    # ---------- 解析 pipeline ----------

    @staticmethod
    def _parse_output_to_plan(output: str, request: VolunteerRequest) -> VolunteerPlan:
        """将 LLM 输出文本解析为 VolunteerPlan（失败时降级）"""
        json_str = extract_json(output)
        if json_str is None:
            print("⚠️  [Agent] 无法从输出中提取 JSON")
            print(f"   前 300 字符: {output[:300]}")
            return build_fallback_plan(request)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ [Agent] JSON 解析失败: {e}")
            return build_fallback_plan(request)

        plan = plan_from_dict(data)
        if plan is None:
            print("⚠️  [Agent] 解析后方案为空")
            return build_fallback_plan(request)

        # 省份校验（双保险的 Python 层）
        plan = filter_schools_by_province(plan, request.province)

        # 跨档位去重（同一所学校只保留首次出现的档位）
        plan = deduplicate_across_tiers(plan)

        return plan

    # ---------- 日志 ----------

    @staticmethod
    def _print_start_log(request: VolunteerRequest):
        print(f"\n{'='*60}")
        print(f"🎓 [VolunteerAgent] 开始生成志愿方案")
        print(f"   省份: {request.province} | 分数: {request.score}分")
        print(f"   类别: {request.subject_category} | 意向: {request.target_major or '不限'}")
        print(f"{'='*60}")


# ======================================================================
# 单例入口
# ======================================================================

_agent_instance: Optional[VolunteerAgent] = None


def get_volunteer_agent() -> VolunteerAgent:
    """获取 LangChain 志愿填报 Agent 单例"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = VolunteerAgent()
    return _agent_instance
