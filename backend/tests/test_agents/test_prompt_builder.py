"""Tests for prompt_builder — LLM prompt formatting helpers."""

from app.agents.prompt_builder import (
    _format_poi_list,
    _format_rest_list,
    _format_weather_list,
    _format_product_list,
)


class TestFormatPoiList:
    def test_formats_pois_with_all_fields(self):
        pois = [
            {"name": "故宫", "category": "风景名胜", "address": "东城区景山前街4号", "rating": "4.8"},
            {"name": "天坛", "category": "公园", "address": "东城区天坛路", "rating": "4.5"},
        ]
        result = _format_poi_list(pois)
        assert "故宫" in result
        assert "天坛" in result
        assert "东城区" in result

    def test_respects_limit(self):
        pois = [{"name": f"景点{i}", "category": "", "address": "", "rating": ""} for i in range(20)]
        result = _format_poi_list(pois, limit=5)
        lines = result.strip().split("\n")
        assert len(lines) == 5
        assert "景点4" in result
        assert "景点15" not in result


class TestFormatRestList:
    def test_formats_restaurants(self):
        rests = [
            {"name": "全聚德", "category": "中餐", "rating": "4.8"},
        ]
        result = _format_rest_list(rests)
        assert "全聚德" in result


class TestFormatWeatherList:
    def test_formats_weather(self):
        weather = [
            {"date": "2026-05-01", "condition": "晴", "temp_min": "15", "temp_max": "25"},
            {"date": "2026-05-02", "condition": "多云", "temp_min": "12", "temp_max": "22"},
        ]
        result = _format_weather_list(weather)
        assert "2026-05-01" in result
        assert "晴" in result

    def test_formats_empty(self):
        result = _format_weather_list([])
        assert "暂无天气数据" in result


class TestFormatProductList:
    def test_formats_products(self):
        products = [
            {"name": "登山包", "price": 199, "tags": ["户外", "旅行"]},
        ]
        result = _format_product_list(products)
        assert "登山包" in result

    def test_formates_none(self):
        result = _format_product_list(None)
        assert "暂无商品数据" in result
