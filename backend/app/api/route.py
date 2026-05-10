"""Route planning API — get directions between two points."""

from math import sin, cos, sqrt, fabs, atan2, pi

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_current_user
from app.models.user import User
from app.services.amap import amap_service

router = APIRouter(prefix="/route", tags=["route"])


# WGS-84 → GCJ-02 conversion (required because browser GPS is WGS-84 but Amap uses GCJ-02)
_A = 6378245.0
_EE = 0.00669342162296594323


def _transform_lat(x: float, y: float) -> float:
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * sqrt(fabs(x))
    ret += (20.0 * sin(6.0 * x * pi) + 20.0 * sin(2.0 * x * pi)) * 2.0 / 3.0
    ret += (20.0 * sin(y * pi) + 40.0 * sin(y / 3.0 * pi)) * 2.0 / 3.0
    ret += (160.0 * sin(y / 12.0 * pi) + 320.0 * sin(y * pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(x: float, y: float) -> float:
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * sqrt(fabs(x))
    ret += (20.0 * sin(6.0 * x * pi) + 20.0 * sin(2.0 * x * pi)) * 2.0 / 3.0
    ret += (20.0 * sin(x * pi) + 40.0 * sin(x / 3.0 * pi)) * 2.0 / 3.0
    ret += (150.0 * sin(x / 12.0 * pi) + 300.0 * sin(x / 30.0 * pi)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lat: float, lng: float) -> tuple[float, float]:
    """Convert WGS-84 (GPS) coordinates to GCJ-02 (Amap/Google China)."""
    if lat < 0.9 or lat > 55.0 or lng < 72.0 or lng > 137.0:
        return lat, lng  # outside China, no conversion needed
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * pi
    magic = sin(radlat)
    magic = 1.0 - _EE * magic * magic
    sqrtmagic = sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1.0 - _EE)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180.0) / (_A / sqrtmagic * cos(radlat) * pi)
    return lat + dlat, lng + dlng


def gcj02_to_wgs84(lat: float, lng: float) -> tuple[float, float]:
    """Convert GCJ-02 (Amap) back to WGS-84 (for OSM map display)."""
    if lat < 0.9 or lat > 55.0 or lng < 72.0 or lng > 137.0:
        return lat, lng
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * pi
    magic = sin(radlat)
    magic = 1.0 - _EE * magic * magic
    sqrtmagic = sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1.0 - _EE)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180.0) / (_A / sqrtmagic * cos(radlat) * pi)
    return lat - dlat, lng - dlng


class RouteRequest(BaseModel):
    destination_name: str
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    origin_lat: float
    origin_lng: float
    city: str = ""
    mode: str = "transit"  # transit / driving / walking


class RouteStep(BaseModel):
    instruction: str
    distance: str
    duration: str


class RouteResponse(BaseModel):
    distance: str
    duration: str
    mode: str
    steps: list[RouteStep]
    destination_name: str
    maps_url: str
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float


def _format_duration(seconds_str: str) -> str:
    """Convert seconds to human-readable format."""
    try:
        seconds = int(seconds_str)
        if seconds < 60:
            return f"{seconds}秒"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}分钟"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}小时{mins}分钟" if mins else f"{hours}小时"
    except (ValueError, TypeError):
        return seconds_str


def _format_distance(meters_str: str) -> str:
    """Convert meters to human-readable format."""
    try:
        meters = int(meters_str)
        if meters < 1000:
            return f"{meters}米"
        km = meters / 1000
        return f"{km:.1f}公里"
    except (ValueError, TypeError):
        return meters_str


def _build_maps_url(
    origin_lat: float, origin_lng: float,
    dest_name: str, dest_lat: Optional[float], dest_lng: Optional[float],
) -> str:
    """Build a maps deep link. Prefer Amap, fallback to Google Maps."""
    if dest_lat and dest_lng:
        return (
            f"https://uri.amap.com/navigation?"
            f"from={origin_lng},{origin_lat}&to={dest_lng},{dest_lat}"
            f"&mode=transit&coordinate=gaode"
        )
    # Search-based link when coordinates aren't available
    import urllib.parse
    return (
        f"https://uri.amap.com/search?"
        f"keyword={urllib.parse.quote(dest_name)}"
    )


@router.post("", summary="Plan route", description="Get directions between origin and destination using Amap. Supports transit/driving/walking modes.", response_model=RouteResponse)
async def plan_route(
    payload: RouteRequest,
    current_user: User = Depends(get_current_user),
):
    """Get route directions from origin to destination."""

    origin = (payload.origin_lng, payload.origin_lat)
    # Convert GPS (WGS-84) → GCJ-02 for Amap API
    gcj_lat, gcj_lng = wgs84_to_gcj02(payload.origin_lat, payload.origin_lng)
    origin = (gcj_lng, gcj_lat)
    dest_lat = payload.destination_lat
    dest_lng = payload.destination_lng

    # Geocode destination if coordinates not provided
    if dest_lat is None or dest_lng is None:
        geo = await amap_service.geocode(payload.destination_name, city=payload.city or None)
        if geo and geo.get("longitude") and geo.get("latitude"):
            dest_lng = geo["longitude"]
            dest_lat = geo["latitude"]

    if dest_lat is None or dest_lng is None:
        raise HTTPException(
            status_code=400,
            detail=f"无法找到「{payload.destination_name}」的位置信息",
        )

    destination = (dest_lng, dest_lat)

    try:
        result = await amap_service.get_direction(origin, destination, mode=payload.mode)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"路线规划失败: {str(e)}")

    steps = []
    for s in result.get("steps", []):
        steps.append(RouteStep(
            instruction=s.get("instruction", ""),
            distance=_format_distance(s.get("distance", "0")),
            duration=_format_duration(s.get("duration", "0")),
        ))

    maps_url = _build_maps_url(
        gcj_lat, gcj_lng,
        payload.destination_name, dest_lat, dest_lng,
    )

    # Return WGS-84 coords to frontend (for correct display on OSM)
    # Origin was already WGS-84 from GPS; destination came from Amap (GCJ-02) so convert back
    dest_wgs_lat, dest_wgs_lng = gcj02_to_wgs84(dest_lat, dest_lng)

    return RouteResponse(
        distance=_format_distance(result.get("distance", "0")),
        duration=_format_duration(result.get("duration", "0")),
        mode=payload.mode,
        steps=steps,
        destination_name=payload.destination_name,
        maps_url=maps_url,
        origin_lat=payload.origin_lat,
        origin_lng=payload.origin_lng,
        destination_lat=dest_wgs_lat,
        destination_lng=dest_wgs_lng,
    )
