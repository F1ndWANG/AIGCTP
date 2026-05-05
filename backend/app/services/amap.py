"""高德地图 API 服务

API 文档: https://lbs.amap.com/api/webservice/guide/api/search
"""
from typing import Optional

import httpx

from app.core.config import settings


class AmapService:
    BASE_URL = "https://restapi.amap.com/v3"

    def __init__(self):
        self.api_key = settings.AMAP_API_KEY
        self.client = httpx.AsyncClient(timeout=10.0)

    async def _get(self, path: str, params: dict) -> dict:
        params["key"] = self.api_key
        resp = await self.client.get(f"{self.BASE_URL}{path}", params=params)
        data = resp.json()
        if data.get("status") != "1":
            raise Exception(f"Amap API error: {data.get('info', 'unknown')}")
        return data

    async def search_poi(
        self,
        keywords: str,
        city: Optional[str] = None,
        types: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict]:
        """POI (Point of Interest) 搜索"""
        params = {
            "keywords": keywords,
            "offset": page_size,
            "page": page,
            "extensions": "all",
        }
        if city:
            params["city"] = city
        if types:
            params["types"] = types

        data = await self._get("/place/text", params)
        pois = data.get("pois", [])
        results = []
        for poi in pois:
            location = poi.get("location", "").split(",")
            results.append({
                "poi_id": poi.get("id"),
                "name": poi.get("name"),
                "longitude": float(location[0]) if len(location) > 0 else None,
                "latitude": float(location[1]) if len(location) > 1 else None,
                "category": poi.get("type", "").split(";")[0] if poi.get("type") else "",
                "address": poi.get("address", ""),
                "phone": poi.get("tel", ""),
                "rating": poi.get("biz_ext", {}).get("rating"),
                "opening_hours": poi.get("biz_ext", {}).get("opentime", ""),
                "images": [img for img in poi.get("images", "").split("|") if img] if poi.get("images") else [],
                "tags": poi.get("type", "").split(";") if poi.get("type") else [],
            })
        return results

    async def search_around(
        self,
        longitude: float,
        latitude: float,
        radius: int = 1000,
        types: Optional[str] = None,
        page_size: int = 20,
    ) -> list[dict]:
        """周边搜索"""
        params = {
            "location": f"{longitude},{latitude}",
            "radius": radius,
            "offset": page_size,
            "extensions": "all",
        }
        if types:
            params["types"] = types

        data = await self._get("/place/around", params)
        pois = data.get("pois", [])
        results = []
        for poi in pois:
            location = poi.get("location", "").split(",")
            results.append({
                "poi_id": poi.get("id"),
                "name": poi.get("name"),
                "longitude": float(location[0]) if len(location) > 0 else None,
                "latitude": float(location[1]) if len(location) > 1 else None,
                "category": poi.get("type", "").split(";")[0] if poi.get("type") else "",
                "address": poi.get("address", ""),
                "distance": poi.get("distance"),
                "rating": poi.get("biz_ext", {}).get("rating"),
                "tags": poi.get("type", "").split(";") if poi.get("type") else [],
            })
        return results

    async def search_restaurants(
        self,
        city: str,
        keywords: Optional[str] = None,
        page_size: int = 20,
    ) -> list[dict]:
        """搜索餐厅"""
        types = "餐饮服务"
        if keywords:
            return await self.search_poi(keywords, city=city, types=types, page_size=page_size)
        return await self.search_poi("餐厅", city=city, types=types, page_size=page_size)

    async def search_scenic_spots(
        self,
        city: str,
        page_size: int = 30,
    ) -> list[dict]:
        """搜索景点"""
        return await self.search_poi("景点", city=city, types="风景名胜", page_size=page_size)

    async def search_hotels(
        self,
        city: str,
        page_size: int = 20,
    ) -> list[dict]:
        """搜索住宿"""
        return await self.search_poi("酒店", city=city, types="住宿服务", page_size=page_size)

    @staticmethod
    def _safe_int(val, default=0):
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    async def get_direction(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str = "transit",
    ) -> dict:
        """路径规划: driving/walking/bicycling/transit

        Returns dict with distance, duration, and human-readable steps.
        """
        params = {
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
            "strategy": 0,
        }
        if mode == "transit":
            data = await self._get("/direction/transit/integrated", {**params, "city": ""})
        elif mode == "driving":
            data = await self._get("/direction/driving", params)
        elif mode == "walking":
            data = await self._get("/direction/walking", params)
        else:
            data = await self._get("/direction/driving", params)

        steps = []
        distance = "0"
        duration = "0"

        if mode == "transit":
            transits = data.get("route", {}).get("transits", [])
            if transits:
                total_dist = 0
                total_dur = 0
                for segment in transits[0].get("segments", []):
                    if "walking" in segment:
                        w = segment["walking"]
                        for step in w.get("steps", []):
                            steps.append({
                                "instruction": step.get("instruction", "") or "",
                                "distance": str(self._safe_int(step.get("distance"))),
                                "duration": str(self._safe_int(step.get("duration"))),
                            })
                            total_dist += self._safe_int(step.get("distance"))
                            total_dur += self._safe_int(step.get("duration"))
                    if "bus" in segment:
                        b = segment["bus"]
                        bus_line = (b.get("buslines") or [{}])[0]
                        dep = bus_line.get("departure_stop", {}) or {}
                        arr = bus_line.get("arrival_stop", {}) or {}
                        dep_name = dep.get("name", "") if isinstance(dep, dict) else ""
                        arr_name = arr.get("name", "") if isinstance(arr, dict) else ""
                        line_name = bus_line.get("name", "") or ""
                        steps.append({
                            "instruction": f"乘坐 {line_name} ({dep_name} → {arr_name})",
                            "distance": str(self._safe_int(bus_line.get("distance"))),
                            "duration": str(self._safe_int(bus_line.get("duration"))),
                        })
                        total_dist += self._safe_int(bus_line.get("distance"))
                        total_dur += self._safe_int(bus_line.get("duration"))
                    if "railway" in segment:
                        r = segment["railway"]
                        r_line = (r.get("lines") or [{}])[0]
                        dep = r_line.get("departure_stop", {}) or {}
                        arr = r_line.get("arrival_stop", {}) or {}
                        dep_name = dep.get("name", "") if isinstance(dep, dict) else ""
                        arr_name = arr.get("name", "") if isinstance(arr, dict) else ""
                        steps.append({
                            "instruction": f"乘坐 {r_line.get('name', '')} ({dep_name} → {arr_name})",
                            "distance": str(self._safe_int(r_line.get("distance"))),
                            "duration": str(self._safe_int(r_line.get("duration"))),
                        })
                        total_dist += self._safe_int(r_line.get("distance"))
                        total_dur += self._safe_int(r_line.get("duration"))
                distance = str(total_dist)
                duration = str(total_dur)
        else:
            route = data.get("route", {})
            paths = route.get("paths", [])
            if paths:
                distance = paths[0].get("distance", "0") or "0"
                duration = paths[0].get("duration", "0") or "0"
                for step in paths[0].get("steps", []):
                    steps.append({
                        "instruction": step.get("instruction", "") or "",
                        "distance": str(self._safe_int(step.get("distance"))),
                        "duration": str(self._safe_int(step.get("duration"))),
                    })

        return {
            "distance": distance,
            "duration": duration,
            "steps": steps,
        }

    async def geocode(self, address: str, city: Optional[str] = None) -> Optional[dict]:
        """地理编码: 地址 → 经纬度"""
        params = {"address": address}
        if city:
            params["city"] = city
        data = await self._get("/geocode/geo", params)
        geocodes = data.get("geocodes", [])
        if not geocodes:
            return None
        location = geocodes[0].get("location", "").split(",")
        return {
            "longitude": float(location[0]) if len(location) > 0 else None,
            "latitude": float(location[1]) if len(location) > 1 else None,
            "formatted_address": geocodes[0].get("formatted_address", ""),
        }


amap_service = AmapService()
