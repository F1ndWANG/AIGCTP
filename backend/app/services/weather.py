"""和风天气 API 服务

API 文档: https://dev.qweather.com/docs/api/
"""
from typing import Optional
import httpx

from app.core.config import settings


class QWeatherService:
    API_HOST = "jj69388r6f.re.qweatherapi.com"

    def __init__(self):
        self.api_key = settings.QWEATHER_API_KEY
        self.client = httpx.AsyncClient(timeout=10.0)

    async def _get(self, path: str, params: dict) -> dict:
        params["key"] = self.api_key
        url = f"https://{self.API_HOST}{path}"
        resp = await self.client.get(url, params=params)
        data = resp.json()
        if data.get("code") != "200":
            raise Exception(f"QWeather API error: code={data.get('code')}")
        return data

    async def get_city_id(self, city: str) -> Optional[str]:
        """城市名称 → 城市ID"""
        data = await self._get("/geo/v2/city/lookup", {"location": city})
        locations = data.get("location", [])
        return locations[0]["id"] if locations else None

    async def get_weather_forecast(self, city: str, days: int = 3) -> list[dict]:
        """获取天气预报 (3天/7天)"""
        city_id = await self.get_city_id(city)
        if not city_id:
            return []

        data = await self._get("/v7/weather/3d", {"location": city_id})
        daily = data.get("daily", [])
        results = []
        for d in daily[:days]:
            results.append({
                "date": d.get("fxDate"),
                "sunrise": d.get("sunrise"),
                "sunset": d.get("sunset"),
                "temp_max": d.get("tempMax"),
                "temp_min": d.get("tempMin"),
                "condition": d.get("textDay"),
                "condition_night": d.get("textNight"),
                "wind_dir": d.get("windDirDay"),
                "wind_scale": d.get("windScaleDay"),
                "humidity": d.get("humidity"),
                "precipitation": d.get("precip"),
                "uv_index": d.get("uvIndex"),
            })
        return results


qweather_service = QWeatherService()
