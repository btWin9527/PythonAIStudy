"""地图服务API路由"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from typing import Optional
import httpx
from ...models.schemas import (
    POISearchRequest,
    POISearchResponse,
    RouteRequest,
    RouteResponse,
    WeatherResponse
)
from ...services.amap_service import get_amap_service
from ...config import get_settings

router = APIRouter(prefix="/map", tags=["地图服务"])


@router.get(
    "/poi",
    response_model=POISearchResponse,
    summary="搜索POI",
    description="根据关键词搜索POI(兴趣点)"
)
async def search_poi(
    keywords: str = Query(..., description="搜索关键词", example="故宫"),
    city: str = Query(..., description="城市", example="北京"),
    citylimit: bool = Query(True, description="是否限制在城市范围内")
):
    """
    搜索POI
    
    Args:
        keywords: 搜索关键词
        city: 城市
        citylimit: 是否限制在城市范围内
        
    Returns:
        POI搜索结果
    """
    try:
        # 获取服务实例
        service = get_amap_service()
        
        # 搜索POI
        pois = service.search_poi(keywords, city, citylimit)
        
        return POISearchResponse(
            success=True,
            message="POI搜索成功",
            data=pois
        )
        
    except Exception as e:
        print(f"❌ POI搜索失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"POI搜索失败: {str(e)}"
        )


@router.get(
    "/weather",
    response_model=WeatherResponse,
    summary="查询天气",
    description="查询指定城市的天气信息"
)
async def get_weather(
    city: str = Query(..., description="城市名称", example="北京")
):
    """
    查询天气
    
    Args:
        city: 城市名称
        
    Returns:
        天气信息
    """
    try:
        # 获取服务实例
        service = get_amap_service()
        
        # 查询天气
        weather_info = service.get_weather(city)
        
        return WeatherResponse(
            success=True,
            message="天气查询成功",
            data=weather_info
        )
        
    except Exception as e:
        print(f"❌ 天气查询失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"天气查询失败: {str(e)}"
        )


@router.post(
    "/route",
    response_model=RouteResponse,
    summary="规划路线",
    description="规划两点之间的路线"
)
async def plan_route(request: RouteRequest):
    """
    规划路线
    
    Args:
        request: 路线规划请求
        
    Returns:
        路线信息
    """
    try:
        # 获取服务实例
        service = get_amap_service()
        
        # 规划路线
        route_info = service.plan_route(
            origin_address=request.origin_address,
            destination_address=request.destination_address,
            origin_city=request.origin_city,
            destination_city=request.destination_city,
            route_type=request.route_type
        )
        
        return RouteResponse(
            success=True,
            message="路线规划成功",
            data=route_info
        )
        
    except Exception as e:
        print(f"❌ 路线规划失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"路线规划失败: {str(e)}"
        )


@router.get(
    "/geocode",
    summary="地理编码",
    description="根据地址获取经纬度,用于补全缺失的 location 字段"
)
async def geocode_address(
    address: str = Query(..., description="要编码的地址,如 '太原市迎泽区' 或 '晋祠'"),
    city: Optional[str] = Query(None, description="所在城市(可选,提高精度)")
):
    """
    调用高德地理编码 API(`v3/geocode/geo`)将地址转为经纬度
    文档: https://lbs.amap.com/api/webservice/guide/api/georegeo
    """
    try:
        settings = get_settings()
        api_key = settings.amap_api_key
        if not api_key:
            raise HTTPException(status_code=500, detail="AMAP_API_KEY 未配置")

        params = {
            "key": api_key,
            "address": address,
            "output": "JSON",
        }
        if city:
            params["city"] = city

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://restapi.amap.com/v3/geocode/geo", params=params)

        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"高德返回 {resp.status_code}")

        data = resp.json()
        if data.get("status") != "1":
            # 高德明确拒绝(如 INVALID_USER_KEY 等)
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "info": data.get("info", "未说明"),
                    "infocode": data.get("infocode"),
                    "data": None
                }
            )

        geocodes = data.get("geocodes", [])
        if not geocodes:
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "info": "无结果",
                    "data": None
                }
            )

        first = geocodes[0]
        location_str = first.get("location", "")  # "lng,lat"
        try:
            lng_str, lat_str = location_str.split(",")
            longitude = float(lng_str)
            latitude = float(lat_str)
        except Exception:
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "info": f"location 字段解析失败: {location_str}",
                    "data": None
                }
            )

        return {
            "success": True,
            "message": "地理编码成功",
            "data": {
                "address": address,
                "city": city,
                "longitude": longitude,
                "latitude": latitude,
                "formatted_address": first.get("formatted_address", address),
                "level": first.get("level", "")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 地理编码失败: {e}")
        raise HTTPException(status_code=500, detail=f"地理编码失败: {str(e)}")


@router.get(
    "/health",
    summary="健康检查",
    description="检查地图服务是否正常"
)
async def health_check():
    """健康检查"""
    try:
        # 检查服务是否可用
        service = get_amap_service()

        return {
            "status": "healthy",
            "service": "map-service",
            "mcp_tools_count": len(service.mcp_tool._available_tools)
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"服务不可用: {str(e)}"
        )


@router.get(
    "/static",
    summary="获取静态地图图片",
    description="通过高德静态地图 API 生成一张含标记点和连线的完整地图图片(PNG)"
)
async def get_static_map(
    center: str = Query(..., description="地图中心点 'lng,lat'"),
    zoom: int = Query(12, description="缩放级别 3-18"),
    size: str = Query("800*500", description="图片尺寸 width*height"),
    markers: Optional[str] = Query(None, description="标记点 JSON 数组字符串,每个元素 {lng, lat, name, color, label}"),
    paths: Optional[str] = Query(None, description="路径 JSON 数组,元素 [{lng, lat}, ...]"),
    map_style: str = Query("normal", description="地图样式: normal/dark/light")
):
    """
    调用高德静态地图 API(`v3/staticmap`)生成 PNG 图片

    文档: https://lbs.amap.com/api/webservice/guide/api/staticmaps
    """
    try:
        settings = get_settings()
        # 优先使用专门的 Web 服务 Key,其次退化到 amap_api_key
        api_key = settings.amap_api_key
        if not api_key:
            raise HTTPException(status_code=500, detail="AMAP_API_KEY 未配置")

        import json as _json

        # 构造 markers 参数（高德格式: mid,0x4CAF50,1:lng,lat;lng,lat）
        markers_param_parts = []
        if markers:
            try:
                marker_list = _json.loads(markers) if isinstance(markers, str) else markers
                # 限制最多 10 个标记
                marker_list = marker_list[:10]
                coords_list: list = []
                for m in marker_list:
                    if m.get('lng') is None or m.get('lat') is None:
                        continue
                    coords_list.append(f"{m['lng']:.6f},{m['lat']:.6f}")
                if coords_list:
                    # mid=中等大小, 0x4CAF50=绿色, 数字标签由高德生成
                    markers_param_parts.append(f"mid,0x4CAF50,1:{';'.join(coords_list)}")
            except Exception as ex:
                print(f"[staticmap] markers 解析失败: {ex}")

        # 构造 paths 参数（高德格式: weight,color,transparency,:lng,lat;lng,lat）
        paths_param_parts = []
        if paths:
            try:
                path_list = _json.loads(paths) if isinstance(paths, str) else paths
                # 限制最多 4 条路径
                path_list = path_list[:4]
                for p in path_list:
                    coords = ';'.join(
                        [f"{pt['lng']:.6f},{pt['lat']:.6f}" for pt in p if pt.get('lng') is not None and pt.get('lat') is not None]
                    )
                    if coords:
                        # weight,color,transparency,fillcolor,fillTransparency
                        # 不填充多边形,所以 fillcolor 为空
                        paths_param_parts.append(f"5,0x1890ff,1,,:{coords}")
            except Exception as ex:
                print(f"[staticmap] paths 解析失败: {ex}")

        # 组合查询参数
        query_parts = [
            f"key={api_key}",
            f"location={center}",
            f"size={size}",
            f"zoom={zoom}",
            "scale=2",
            "type=png",
        ]
        if markers_param_parts:
            query_parts.append("markers=" + "|".join(markers_param_parts))
        if paths_param_parts:
            query_parts.append("paths=" + "|".join(paths_param_parts))

        # mapStyle
        style_map = {"normal": "normal", "dark": "dark", "light": "light"}
        query_parts.append(f"style={style_map.get(map_style, 'normal')}")

        url = "https://restapi.amap.com/v3/staticmap?" + "&".join(query_parts)
        print(f"[staticmap] GET {url[:200]}...")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"高德静态地图 API 返回 {resp.status_code}: {resp.text[:300]}"
            )

        ctype = resp.headers.get("content-type", "")
        if "image" not in ctype:
            raise HTTPException(
                status_code=502,
                detail=f"高德静态地图返回非图片: {resp.text[:300]}"
            )

        return Response(
            content=resp.content,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=300",
                "Access-Control-Allow-Origin": "*"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 静态地图生成失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"静态地图生成失败: {str(e)}"
        )

