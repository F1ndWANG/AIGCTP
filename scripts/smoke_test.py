"""Small HTTP smoke test that does not require Docker or k6.

Run against an already running backend:
    python scripts/smoke_test.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import random
import string
import sys
import urllib.error
import urllib.request


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, str]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body


def _assert_status(name: str, status: int, expected: set[int], body: str = "") -> None:
    if status not in expected:
        raise AssertionError(f"{name} returned {status}, expected {sorted(expected)}. Body: {body[:500]}")
    print(f"[ok] {name}: {status}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    username = f"smoke_{suffix}"
    password = "SmokeTest1"

    checks = [
        ("health", "GET", "/health", None, {200}),
        ("readiness", "GET", "/api/v1/health/ready", None, {200, 503}),
        (
            "register",
            "POST",
            "/api/v1/auth/register",
            {"username": username, "password": password, "display_name": "Smoke Test"},
            {201, 400, 409},
        ),
        (
            "login",
            "POST",
            "/api/v1/auth/login",
            {"username": username, "password": password},
            {200},
        ),
    ]

    try:
        for name, method, path, payload, expected in checks:
            status, body = _request(method, f"{base_url}{path}", payload)
            _assert_status(name, status, expected, body)
    except Exception as exc:
        print(f"[fail] {exc}", file=sys.stderr)
        return 1

    print("[ok] smoke test completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
