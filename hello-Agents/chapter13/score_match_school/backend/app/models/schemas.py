"""志愿填报数据模型"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ============ 请求模型 ============

class VolunteerRequest(BaseModel):
    """志愿填报请求"""
    province: str = Field(..., description="高考省份", example="四川")
    score: int = Field(..., description="高考分数", ge=100, le=750, example=580)
    target_major: Optional[str] = Field(default="", description="意向专业（可选）", example="会计")
    subject_category: str = Field(
        ...,
        description="报考类别: science(理科/物理类) / arts(文科/历史类) / art(艺术类)",
        pattern="^(science|arts|art)$",
        example="science"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "province": "四川",
                "score": 580,
                "target_major": "会计",
                "subject_category": "science"
            }
        }


# ============ 响应模型 ============

class SchoolMajor(BaseModel):
    """学校+专业组合"""
    school_name: str = Field(..., description="学校名称")
    major_name: str = Field(..., description="专业名称")
    confidence: int = Field(..., description="推荐信心度 0-100", ge=0, le=100)
    reason: str = Field(..., description="推荐理由")
    reference_score: Optional[int] = Field(
        default=None,
        description="最近3年该省份该专业的平均投档分数线",
        example=585
    )
    school_type: Optional[str] = Field(
        default=None,
        description="院校类型: 综合类/理工类/财经类/师范类/医药类/艺术类/语言类/政法类/农林类/军事类/民族类",
        example="综合类"
    )
    school_level: Optional[str] = Field(
        default=None,
        description="院校层级: 985/211/双一流/普通本科",
        example="211"
    )
    reference_sources: Optional[List[str]] = Field(
        default=None,
        description="数据来源URL列表（联网搜索结果）"
    )


class VolunteerTier(BaseModel):
    """志愿档位（冲/稳/保）"""
    tier_type: str = Field(..., description="档位类型: chong/wen/bao")
    tier_label: str = Field(..., description="档位中文标签")
    description: str = Field(..., description="该批次策略说明")
    schools: List[SchoolMajor] = Field(default=[], description="学校+专业列表")


class VolunteerPlan(BaseModel):
    """完整志愿填报方案"""
    summary: str = Field(..., description="总体志愿填报策略建议")
    tiers: List[VolunteerTier] = Field(..., description="冲/稳/保三档方案")
    disclaimer: Optional[str] = Field(
        default="以上推荐基于AI分析和联网搜索结果生成，仅供参考。历年分数线、招生计划等信息可能随年度调整，实际填报请务必以各省教育考试院官方发布、目标院校招生官网为准。",
        description="免责声明"
    )


class VolunteerPlanResponse(BaseModel):
    """志愿填报响应"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="消息")
    data: Optional[VolunteerPlan] = Field(default=None, description="志愿方案数据")


# ============ 错误响应 ============

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(default=False, description="是否成功")
    message: str = Field(..., description="错误消息")
    error_code: Optional[str] = Field(default=None, description="错误代码")
