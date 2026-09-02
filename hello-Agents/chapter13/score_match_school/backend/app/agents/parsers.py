"""志愿填报 Agent 解析与校验工具集

职责：
1. JSON 提取与解析（从 LLM 输出中稳健提取 JSON）
2. 数据模型转换（dict → VolunteerPlan）
3. 省份校验过滤（双保险中的 Python 后处理层）
4. 降级方案构建（Agent 调用失败时返回占位数据）
5. 学校名校验

这些函数都是 **纯函数**，无状态、可独立单测。
"""

import json
import re
from typing import Any, Optional

from .constants import (
    DEFAULT_DISCLAIMER,
    PROVINCE_KEYWORDS,
    SCHOOL_SUFFIXES,
)
from ..models.schemas import (
    SchoolMajor,
    VolunteerPlan,
    VolunteerRequest,
    VolunteerTier,
)


# ======================================================================
# 1. JSON 提取
# ======================================================================

def extract_json(text: str) -> Optional[str]:
    """从 LLM 输出中提取 JSON 字符串（三种策略依次尝试）

    策略优先级：
    1. 直接是 JSON（首尾为花括号）
    2. ```json ... ``` 代码块
    3. 从第一个 { 到最后一个 } 截取
    """
    if not text:
        return None
    text = text.strip()

    # 1) 直接是 JSON
    if text.startswith('{') and text.endswith('}'):
        return text

    # 2) ```json ... ``` 代码块
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # 3) 从第一个 { 到最后一个 }
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]

    return None


# ======================================================================
# 2. confidence 解析
# ======================================================================

def parse_confidence(value: Any) -> int:
    """安全解析 confidence 字段，钳位到 [0, 100]"""
    try:
        v = int(value)
        return max(0, min(100, v))
    except (TypeError, ValueError):
        return 50


# ======================================================================
# 3. 学校名校验
# ======================================================================

def validate_school_name(name: str) -> bool:
    """轻量级校验学校名称真实性

    规则：
    - 长度 4~20
    - 必须包含至少一个学校后缀（大学/学院/职业/...）
    """
    if not name or len(name) < 4 or len(name) > 20:
        return False
    if not any(suffix in name for suffix in SCHOOL_SUFFIXES):
        return False
    return True


# ======================================================================
# 4. 省份匹配检查（核心规则）
# ======================================================================

def check_province_match(
    school_name: str,
    target_province: str,
    school_level: Optional[str] = None,  # 保留签名兼容调用方
) -> bool:
    """
    省份归属检查（报考目标省份模式）

    三条规则：
    1. 含目标省关键词（省名 / 省会 / 中心城市）→ ✅ 保留
    2. 含其他省关键词（任何层级，不允许跨省）→ ❌ 过滤
    3. 不含任何省关键词（如清华大学/东南大学/中山大学）→ ✅ 保留
       → 这类靠 Prompt 硬约束 + LLM 搜索"XX省大学名单"来保证正确性

    Python 后处理的定位：**精确排除带他省地名的学校**，避免明显串省。
    不含省名的无地域名校，交给 Prompt 约束兜底。
    """
    if not school_name or not target_province:
        return True  # 空数据交给下游处理

    target_keywords = PROVINCE_KEYWORDS.get(target_province, [target_province])

    # 规则 1: 含目标省关键词 → 保留
    if any(kw in school_name for kw in target_keywords):
        return True

    # 规则 2: 含其他省关键词 → 过滤（不再有 985 例外）
    for province, keywords in PROVINCE_KEYWORDS.items():
        if province == target_province:
            continue
        if any(kw in school_name for kw in keywords):
            return False

    # 规则 3: 不含任何省关键词 → 保留（LLM Prompt 兜底）
    return True


# ======================================================================
# 5. 方案整体省份过滤
# ======================================================================

def filter_schools_by_province(
    plan: VolunteerPlan,
    target_province: str,
) -> VolunteerPlan:
    """
    对方案中的每所学校执行省份校验过滤

    同时执行：
    - 学校名校验（validate_school_name）
    - 省份匹配检查（check_province_match）
    """
    filtered_tiers = []
    removed_count = 0

    for tier in plan.tiers:
        kept_schools = []
        for s in tier.schools:
            # 学校名真实性
            if not validate_school_name(s.school_name):
                removed_count += 1
                print(f"  [过滤] 学校名不真实: {s.school_name}")
                continue

            # 省份匹配
            if not check_province_match(s.school_name, target_province, s.school_level):
                removed_count += 1
                print(f"  [过滤] 省份不匹配: {s.school_name} (目标:{target_province}, level:{s.school_level})")
                continue

            kept_schools.append(s)

        filtered_tiers.append(VolunteerTier(
            tier_type=tier.tier_type,
            tier_label=tier.tier_label,
            description=tier.description,
            schools=kept_schools,
        ))

    if removed_count > 0:
        print(f"ℹ️  省份校验过滤掉 {removed_count} 所不符合条件的院校")

    return VolunteerPlan(
        summary=plan.summary,
        tiers=filtered_tiers,
        disclaimer=plan.disclaimer or DEFAULT_DISCLAIMER,
    )


# ======================================================================
# 6. 跨档位去重
# ======================================================================

def deduplicate_across_tiers(plan: VolunteerPlan) -> VolunteerPlan:
    """
    跨档位去重：同一所学校只保留**首次出现**的档位

    规则：
    - 按 冲档 → 稳档 → 保档 的顺序遍历
    - 学校名（含"学校+专业"组合）首次出现保留，后续重复移除
    - LLM 有概率无视 Prompt 的"禁止跨档位重复"约束，此处 Python 兜底
    """
    seen: set = set()
    deduped_tiers = []
    removed_count = 0

    for tier in plan.tiers:
        kept_schools = []
        for s in tier.schools:
            # 以 学校名+专业名 作为唯一键；专业为"不限"时仅按学校名去重
            major = (s.major_name or "").strip()
            key = s.school_name.strip() if major in ("", "不限") else f"{s.school_name.strip()}|{major}"

            if key in seen:
                removed_count += 1
                print(f"  [去重] 移除跨档位重复: {s.school_name} (出现于 {tier.tier_label})")
                continue

            seen.add(key)
            kept_schools.append(s)

        deduped_tiers.append(VolunteerTier(
            tier_type=tier.tier_type,
            tier_label=tier.tier_label,
            description=tier.description,
            schools=kept_schools,
        ))

    if removed_count > 0:
        print(f"ℹ️  跨档位去重移除 {removed_count} 条重复记录")

    return VolunteerPlan(
        summary=plan.summary,
        tiers=deduped_tiers,
        disclaimer=plan.disclaimer or DEFAULT_DISCLAIMER,
    )


# ======================================================================
# 7. dict → VolunteerPlan
# ======================================================================

def plan_from_dict(data: dict) -> Optional[VolunteerPlan]:
    """将 JSON dict 转换为 VolunteerPlan 对象

    跳过无效条目，遇到空 tiers 返回 None（由调用方决定是否降级）。
    """
    tiers = []
    for tier_data in data.get("tiers", []):
        schools = []
        for s in tier_data.get("schools", []):
            try:
                school = SchoolMajor(
                    school_name=str(s.get("school_name", "")),
                    major_name=str(s.get("major_name", "")),
                    confidence=parse_confidence(s.get("confidence")),
                    reason=str(s.get("reason", "")),
                    reference_score=s.get("reference_score"),
                    school_type=s.get("school_type"),
                    school_level=s.get("school_level"),
                    reference_sources=s.get("reference_sources"),
                )
                schools.append(school)
            except Exception as e:
                print(f"⚠️  跳过无效学校数据: {e}")

        tiers.append(VolunteerTier(
            tier_type=str(tier_data.get("tier_type", "")),
            tier_label=str(tier_data.get("tier_label", "")),
            description=str(tier_data.get("description", "")),
            schools=schools,
        ))

    if not tiers:
        return None

    return VolunteerPlan(
        summary=str(data.get("summary", "")),
        tiers=tiers,
        disclaimer=data.get("disclaimer"),
    )


# ======================================================================
# 8. 降级方案
# ======================================================================

def build_fallback_plan(request: VolunteerRequest) -> VolunteerPlan:
    """Agent 调用失败时的降级占位方案

    每个档位放 1 条占位记录，提示用户稍后重试。
    """
    target_major = request.target_major or "热门专业"
    tier_builders = [
        ("chong", "冲刺院校", "参考线略高于考生分数，有一定概率录取的院校", request.score + 15),
        ("wen", "稳妥院校", "分数匹配度较高，录取概率大的院校", request.score),
        ("bao", "保底院校", "分数明显高于投档线，确保录取的院校", request.score - 15),
    ]

    tiers = []
    for tier_type, tier_label, desc, ref_score in tier_builders:
        tiers.append(VolunteerTier(
            tier_type=tier_type,
            tier_label=tier_label,
            description=desc,
            schools=[SchoolMajor(
                school_name="AI 服务暂时不可用，请稍后重试",
                major_name=target_major,
                confidence=50,
                reason="Agent 服务暂时不可用，请稍后重新生成以获取完整智能推荐方案",
                reference_score=ref_score,
                school_type="综合类",
                school_level="普通本科",
            )],
        ))

    return VolunteerPlan(
        summary=(
            f"AI 服务暂时不可用。当前为降级占位方案，"
            f"请稍后重试以获取 {request.province}{request.score} 分 {request.subject_category} 的完整智能推荐。"
        ),
        tiers=tiers,
        disclaimer="⚠️ AI 服务暂时不可用，以上为占位数据。",
    )
