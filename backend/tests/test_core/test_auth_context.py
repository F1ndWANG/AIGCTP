from app.core.auth_context import (
    ACCESS_COOKIE,
    AUTH_COOKIE_PATH,
    LEGACY_AUTH_COOKIE_PATHS,
    REFRESH_COOKIE,
    access_token_candidates,
    logout_access_token,
)


def test_access_token_candidates_prefer_cookie_and_deduplicate_header():
    assert access_token_candidates("cookie-token", "header-token") == ("cookie-token", "header-token")
    assert access_token_candidates("same-token", "same-token") == ("same-token",)
    assert access_token_candidates(None, "header-token") == ("header-token",)
    assert access_token_candidates("cookie-token", None) == ("cookie-token",)


def test_logout_access_token_prefers_header_source():
    assert logout_access_token("cookie-token", "header-token") == "header-token"
    assert logout_access_token("cookie-token", None) == "cookie-token"
    assert logout_access_token(None, None) is None


def test_auth_cookie_constants_keep_legacy_paths():
    assert ACCESS_COOKIE == "access_token"
    assert REFRESH_COOKIE == "refresh_token"
    assert AUTH_COOKIE_PATH == "/"
    assert "/api/v1/auth" in LEGACY_AUTH_COOKIE_PATHS
