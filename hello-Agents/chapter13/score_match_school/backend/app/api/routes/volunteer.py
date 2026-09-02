"""志愿填报API路由"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ...models.schemas import (
    VolunteerRequest,
    VolunteerPlanResponse,
    ErrorResponse
)
from ...agents.volunteer_agent import get_volunteer_agent

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/volunteer",
    tags=["volunteer"],
    responses={
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"}
    }
)


@router.post(
    "/generate",
    response_model=VolunteerPlanResponse,
    summary="生成志愿填报方案",
    description="根据考生的省份、分数、意向专业、报考类别，通过AI智能生成冲/稳/保三档志愿填报方案"
)
async def generate_volunteer_plan(
    request: VolunteerRequest
):
    """生成志愿填报方案"""
    try:
        # 参数校验
        if not request.province:
            raise HTTPException(status_code=400, detail="高考省份不能为空")

        if request.score < 100 or request.score > 750:
            raise HTTPException(status_code=400, detail="高考分数必须在100-750之间")

        if request.subject_category not in ("science", "arts", "art"):
            raise HTTPException(
                status_code=400,
                detail="报考类别必须是 science(理科/物理类)、arts(文科/历史类) 或 art(艺术类)"
            )

        # 获取Agent并生成方案
        agent = get_volunteer_agent()

        # 使用线程池同步执行Agent (HelloAgents是同步API)
        loop = asyncio.get_event_loop()
        plan = await loop.run_in_executor(None, agent.generate, request)

        return VolunteerPlanResponse(
            success=True,
            message="志愿方案生成成功",
            data=plan
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成志愿方案失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                success=False,
                message=f"生成志愿方案失败: {str(e)}",
                error_code="GENERATION_FAILED"
            ).model_dump()
        )


@router.get(
    "/provinces",
    summary="获取支持的省份列表"
)
async def get_provinces():
    """返回全国34个省/直辖市/自治区"""
    provinces = [
        "北京", "天津", "上海", "重庆",
        "河北", "山西", "辽宁", "吉林", "黑龙江",
        "江苏", "浙江", "安徽", "福建", "江西", "山东",
        "河南", "湖北", "湖南", "广东", "海南",
        "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾",
        "内蒙古", "广西", "西藏", "宁夏", "新疆",
        "香港", "澳门"
    ]
    return {"success": True, "data": provinces}


@router.get(
    "/health",
    summary="检查志愿Agent是否可用"
)
async def check_agent_health():
    """检查Agent初始化状态"""
    try:
        agent = get_volunteer_agent()
        return {
            "success": True,
            "agent_initialized": agent._initialized,
            "status": "healthy"
        }
    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }
