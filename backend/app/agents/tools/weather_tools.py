"""Weather tools for Travel Agent"""
import datetime
import hashlib

from app.services.weather import qweather_service
from app.core.logging import get_logger

logger = get_logger(__name__)


def _deterministic_int(seed: str, min_val: int, max_val: int) -> int:
    """Generate a deterministic integer from a seed string."""
    h = hashlib.md5(seed.encode()).hexdigest()
    return min_val + (int(h[:8], 16) % (max_val - min_val + 1))


def _deterministic_choice(seed: str, choices: list[str]) -> str:
    """Generate a deterministic choice from a seed string."""
    h = hashlib.md5(seed.encode()).hexdigest()
    return choices[int(h[:8], 16) % len(choices)]


def _fallback_forecast(city: str, days: int = 3) -> list[dict]:
    """Generate mock weather when API is unavailable (season-appropriate)."""
    today = datetime.date.today()
    month = today.month
    # Spring (3-5): 15-25, Summer (6-8): 25-35, Autumn (9-11): 10-25, Winter (12-2): 0-15
    if 3 <= month <= 5:
        base_min, base_max = 15, 25
        conditions_pool = ["晴", "多云", "阴", "小雨", "晴", "多云"]
    elif 6 <= month <= 8:
        base_min, base_max = 25, 35
        conditions_pool = ["晴", "多云", "晴", "雷阵雨", "多云", "晴"]
    elif 9 <= month <= 11:
        base_min, base_max = 10, 25
        conditions_pool = ["晴", "多云", "阴", "小雨", "晴", "多云"]
    else:
        base_min, base_max = 0, 15
        conditions_pool = ["晴", "多云", "阴", "小雪", "晴", "多云"]

    results = []
    for i in range(days):
        day = today + datetime.timedelta(days=i)
        cond = conditions_pool[i % len(conditions_pool)]
        day_seed = f"{city}:{i}"
        temp_min = _deterministic_int(f"{day_seed}:min", base_min, base_min + 5)
        temp_max = _deterministic_int(f"{day_seed}:max", base_max - 5, base_max)
        results.append({
            "date": day.isoformat(),
            "temp_max": str(temp_max),
            "temp_min": str(temp_min),
            "condition": cond,
            "condition_night": cond,
            "wind_dir": _deterministic_choice(f"{day_seed}:wind", ["东南风", "西南风", "东北风", "西北风"]),
            "wind_scale": str(_deterministic_int(f"{day_seed}:scale", 1, 4)),
            "humidity": str(_deterministic_int(f"{day_seed}:humidity", 45, 85)),
            "precipitation": str(_deterministic_int(f"{day_seed}:precip", 0, 30)),
            "uv_index": str(_deterministic_int(f"{day_seed}:uv", 1, 5)),
        })
    return results


async def get_weather_forecast(city: str, days: int = 3) -> list[dict]:
    """获取指定城市的天气预报（带降级）"""
    try:
        return await qweather_service.get_weather_forecast(city, days=days)
    except Exception as e:
        logger.warning("Weather API failed for %s: %s, using fallback", city, e)
        return _fallback_forecast(city, days)


async def get_weather_for_dates(city: str, start_date: str, end_date: str) -> list[dict]:
    """获取指定日期范围的天气预报"""
    start = datetime.date.fromisoformat(start_date)
    end = datetime.date.fromisoformat(end_date)
    days = (end - start).days + 1
    forecast = await get_weather_forecast(city, days=max(days, 3))
    return [d for d in forecast if start_date <= d["date"] <= end_date]
