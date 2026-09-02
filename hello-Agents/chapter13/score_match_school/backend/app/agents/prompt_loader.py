"""Prompt 模板加载器

职责：
1. 从 prompts/ 目录读取 .txt 模板文件
2. 根据请求参数填充模板占位符（{province}、{year-1}、{score} 等）
3. 返回可直接传给 LangChain create_agent 的 system_prompt / human_prompt

模板文件约定：
- volunteer_system.txt   → 系统提示词模板
- volunteer_user.txt     → 用户提示词模板

占位符说明：
- {province} / {score} / {target_major} / {subject_label} → 从 request 动态填充
- {year-1} / {year-2} / {year-3}                         → 近3年实际年份
- {subject_text}                                          → 科目中文（理科/文科/艺术类）
- {school_types} / {school_levels}                        → 枚举值列表（逗号分隔）
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict

from .constants import (
    SCHOOL_TYPE_VALUES,
    SCHOOL_LEVEL_VALUES,
    SUBJECT_CATEGORY_LABELS,
)

# ======================================================================
# 模板文件路径（相对本文件所在目录）
# ======================================================================

_PROMPTS_DIR = Path(__file__).parent / "prompts"

_SYSTEM_TEMPLATE_PATH = _PROMPTS_DIR / "volunteer_system.txt"
_USER_TEMPLATE_PATH = _PROMPTS_DIR / "volunteer_user.txt"


# ======================================================================
# 科目类别 → 中文描述（用于搜索关键词）
# ======================================================================

_SUBJECT_TEXT_MAP: Dict[str, str] = {
    "science": "理科",
    "arts": "文科",
    "art": "艺术类",
}


# ======================================================================
# 内部：加载 + 缓存模板
# ======================================================================

_template_cache: Dict[str, str] = {}


def _load_template(path: Path) -> str:
    """读取 txt 模板文件（带简单缓存）"""
    cache_key = str(path)
    if cache_key in _template_cache:
        return _template_cache[cache_key]

    if not path.exists():
        raise FileNotFoundError(f"Prompt 模板文件不存在: {path}")

    content = path.read_text(encoding="utf-8").strip()
    _template_cache[cache_key] = content
    return content


def _invalidate_cache():
    """清除模板缓存（开发时热更新用）"""
    _template_cache.clear()


# ======================================================================
# 构建 System Prompt
# ======================================================================

def build_system_prompt(
    province: str,
    score: int,
    subject_category: str,
    target_major: str,
    years_str: str,
) -> str:
    """
    填充 system prompt 模板，返回完整系统提示词

    :param province:        考生省份（如 "山西"）
    :param score:           考生分数
    :param subject_category: science / arts / art
    :param target_major:    意向专业（可空）
    :param years_str:       近3年，逗号分隔（如 "2025,2024,2023"）
    :return:                已填充的 system_prompt
    """
    template = _load_template(_SYSTEM_TEMPLATE_PATH)
    year_list = years_str.split(",")

    values = {
        "province": province,
        "score": score,
        "target_major": target_major or "不限",
        "subject_text": _SUBJECT_TEXT_MAP.get(subject_category, "理科"),
        "year-1": year_list[0] if len(year_list) > 0 else str(datetime.now().year - 1),
        "year-2": year_list[1] if len(year_list) > 1 else str(datetime.now().year - 2),
        "year-3": year_list[2] if len(year_list) > 2 else str(datetime.now().year - 3),
        "school_name": "{school_name}",  # 保留为字面量，让 LLM 在搜索时自己填具体校名
        "school_types": "/".join(SCHOOL_TYPE_VALUES),
        "school_levels": "/".join(SCHOOL_LEVEL_VALUES),
    }

    return template.format(**values)


# ======================================================================
# 构建 Human Prompt
# ======================================================================

def build_human_prompt(
    province: str,
    score: int,
    subject_category: str,
    target_major: str,
) -> str:
    """
    填充 user prompt 模板，返回完整用户提示词

    :param province:        考生省份
    :param score:           考生分数
    :param subject_category: science / arts / art
    :param target_major:    意向专业
    :return:                已填充的 human_prompt
    """
    template = _load_template(_USER_TEMPLATE_PATH)

    subject_label = SUBJECT_CATEGORY_LABELS.get(
        subject_category,
        SUBJECT_CATEGORY_LABELS["science"]
    )["label"]

    return template.format(
        province=province,
        score=score,
        subject_label=subject_label,
        target_major=target_major or "不限",
    )
