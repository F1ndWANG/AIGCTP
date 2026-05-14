from app.core import http_paths


def test_api_path_constants_are_composed_from_single_prefix():
    assert http_paths.API_V1_PREFIX == "/api/v1"
    assert http_paths.API_METRICS_PATH == f"{http_paths.API_V1_PREFIX}{http_paths.METRICS_PATH}"
    assert http_paths.API_READY_PATH == f"{http_paths.API_V1_PREFIX}{http_paths.READY_PATH}"
    assert http_paths.API_LLM_HEALTH_PATH == f"{http_paths.API_V1_PREFIX}{http_paths.LLM_HEALTH_PATH}"


def test_operational_exemptions_are_explicit():
    assert http_paths.HEALTH_PATH in http_paths.RATE_LIMIT_EXEMPT_PATHS
    assert http_paths.API_READY_PATH in http_paths.RATE_LIMIT_EXEMPT_PATHS
    assert http_paths.API_LLM_HEALTH_PATH in http_paths.RATE_LIMIT_EXEMPT_PATHS
    assert http_paths.API_METRICS_PATH in http_paths.METRICS_EXEMPT_PATHS
