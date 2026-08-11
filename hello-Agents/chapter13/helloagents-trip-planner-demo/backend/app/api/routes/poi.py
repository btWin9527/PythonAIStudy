"""POI相关API路由"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from ...services.amap_service import get_amap_service
from ...services.unsplash_service import get_unsplash_service

router = APIRouter(prefix="/poi", tags=["POI"])


class POIDetailResponse(BaseModel):
    """POI详情响应"""
    success: bool
    message: str
    data: Optional[dict] = None


@router.get(
    "/detail/{poi_id}",
    response_model=POIDetailResponse,
    summary="获取POI详情",
    description="根据POI ID获取详细信息,包括图片"
)
async def get_poi_detail(poi_id: str):
    """
    获取POI详情
    
    Args:
        poi_id: POI ID
        
    Returns:
        POI详情响应
    """
    try:
        amap_service = get_amap_service()
        
        # 调用高德地图POI详情API
        result = amap_service.get_poi_detail(poi_id)
        
        return POIDetailResponse(
            success=True,
            message="获取POI详情成功",
            data=result
        )
        
    except Exception as e:
        print(f"❌ 获取POI详情失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取POI详情失败: {str(e)}"
        )


@router.get(
    "/search",
    summary="搜索POI",
    description="根据关键词搜索POI"
)
async def search_poi(keywords: str, city: str = "北京"):
    """
    搜索POI

    Args:
        keywords: 搜索关键词
        city: 城市名称

    Returns:
        搜索结果
    """
    try:
        amap_service = get_amap_service()
        result = amap_service.search_poi(keywords, city)

        return {
            "success": True,
            "message": "搜索成功",
            "data": result
        }

    except Exception as e:
        print(f"❌ 搜索POI失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"搜索POI失败: {str(e)}"
        )


@router.get(
    "/photo",
    summary="获取景点图片",
    description="根据景点名称从Unsplash获取图片(返回多张候选,前端去重)"
)
async def get_attraction_photo(name: str):
    """
    获取景点图片

    Args:
        name: 景点名称

    Returns:
        多张候选图片 URL(供前端去重选择)
    """
    try:
        unsplash_service = get_unsplash_service()

        # 优先搜索 景点 + China landmark
        photo_urls = unsplash_service.get_multiple_photos(
            f"{name} China landmark", count=6
        )
        # 不行就用景点名再搜一次
        if not photo_urls:
            photo_urls = unsplash_service.get_multiple_photos(name, count=6)

        # 再不行用 generic
        if not photo_urls:
            photo_urls = unsplash_service.get_multiple_photos(
                "ancient China temple", count=6
            )

        return {
            "success": True,
            "message": "获取图片成功",
            "data": {
                "name": name,
                "photo_urls": photo_urls,        # 多张候选
                "photo_url": photo_urls[0] if photo_urls else None,  # 兼容前端
            }
        }

    except Exception as e:
        print(f"❌ 获取景点图片失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取景点图片失败: {str(e)}"
        )

