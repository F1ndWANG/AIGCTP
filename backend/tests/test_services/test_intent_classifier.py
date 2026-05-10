"""Tests for intent classifier: keyword fast-path detection and parameter extraction."""
from app.services.intent_classifier import (
    _quick_travel_detection,
    _quick_reorder_detection,
    _quick_auto_cart_detection,
    _quick_diet_log_detection,
    _quick_diet_analyze_detection,
    _quick_commerce_detection,
    _quick_restaurant_detection,
    _quick_route_detection,
)


class TestQuickTravelDetection:
    def test_travel_keyword_detected(self):
        assert _quick_travel_detection("给我推荐一个旅游景点") is True

    def test_travel_prefix_detected(self):
        assert _quick_travel_detection("想去北京玩") is True

    def test_suffix_pattern_detected(self):
        assert _quick_travel_detection("北京三日游攻略") is True

    def test_day_trip_detected(self):
        assert _quick_travel_detection("西安二日游推荐") is True

    def test_general_chat_not_travel(self):
        assert _quick_travel_detection("你好，今天天气怎么样") is False

    def test_empty_string_not_travel(self):
        assert _quick_travel_detection("") is False

    def test_food_query_not_travel(self):
        assert _quick_travel_detection("推荐一些健康饮食建议") is False

    def test_weather_query_not_travel(self):
        assert _quick_travel_detection("今天天气怎么样") is False


class TestQuickReorderDetection:
    def test_reorder_keyword_detected(self):
        assert _quick_reorder_detection("我想再买一次") is True

    def test_reorder_repurchase(self):
        assert _quick_reorder_detection("复购上次的商品") is True

    def test_non_reorder_not_detected(self):
        assert _quick_reorder_detection("我想买点东西") is False


class TestQuickAutoCartDetection:
    def test_add_to_cart_detected(self):
        assert _quick_auto_cart_detection("帮我加购这个商品") is True

    def test_purchase_detected(self):
        assert _quick_auto_cart_detection("帮我下单") is True

    def test_stock_up_detected(self):
        assert _quick_auto_cart_detection("囤货一些大米") is True

    def test_non_cart_not_detected(self):
        assert _quick_auto_cart_detection("这个商品怎么样") is False


class TestQuickDietLogDetection:
    def test_breakfast_log_detected(self):
        assert _quick_diet_log_detection("早餐吃了面包和牛奶") is True

    def test_lunch_log_detected(self):
        assert _quick_diet_log_detection("午餐吃了米饭") is True

    def test_diet_record_detected(self):
        assert _quick_diet_log_detection("记录饮食") is True

    def test_non_diet_not_detected(self):
        assert _quick_diet_log_detection("你好") is False


class TestQuickDietAnalyzeDetection:
    def test_diet_analysis_detected(self):
        assert _quick_diet_analyze_detection("分析饮食") is True

    def test_nutrition_analysis_detected(self):
        assert _quick_diet_analyze_detection("营养分析") is True

    def test_calorie_detected(self):
        assert _quick_diet_analyze_detection("卡路里") is True

    def test_non_diet_not_detected(self):
        assert _quick_diet_analyze_detection("你好") is False


class TestQuickRestaurantDetection:
    def test_restaurant_recommend_detected(self):
        assert _quick_restaurant_detection("推荐餐厅") is True

    def test_food_nearby_detected(self):
        assert _quick_restaurant_detection("附近有什么吃的") is True

    def test_delicious_detected(self):
        assert _quick_restaurant_detection("好吃的推荐") is True

    def test_non_restaurant_not_detected(self):
        assert _quick_restaurant_detection("你好") is False


class TestQuickCommerceDetection:
    def test_commerce_keyword_detected(self):
        assert _quick_commerce_detection("推荐商品") is True

    def test_want_to_buy_detected(self):
        assert _quick_commerce_detection("想买") is True

    def test_equipment_detected(self):
        assert _quick_commerce_detection("旅行好物") is True

    def test_non_commerce_not_detected(self):
        assert _quick_commerce_detection("你好") is False


class TestQuickRouteDetection:
    def test_route_detected(self):
        assert _quick_route_detection("路线怎么走") is True

    def test_navigation_detected(self):
        assert _quick_route_detection("导航到北京") is True

    def test_how_to_get_there_detected(self):
        assert _quick_route_detection("怎么去") is True

    def test_non_route_not_detected(self):
        assert _quick_route_detection("你好") is False
