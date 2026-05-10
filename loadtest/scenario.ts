import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

// ── Configuration ──────────────────────────────────────────────

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const LLM_API_KEY = __ENV.LLM_API_KEY || "";

export const options = {
  stages: [
    { duration: "30s", target: 5 },   // Ramp up to 5 VUs
    { duration: "1m", target: 10 },   // Ramp to 10 VUs
    { duration: "2m", target: 20 },   // Ramp to 20 VUs
    { duration: "1m", target: 10 },   // Scale down
    { duration: "30s", target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<5000"],  // 95% of requests under 5s
    http_req_failed: ["rate<0.10"],     // Less than 10% failure rate
    auth_duration: ["p(95)<2000"],
    chat_duration: ["p(95)<30000"],
  },
};

// ── Custom metrics ─────────────────────────────────────────────

const authDuration = new Trend("auth_duration", true);
const chatDuration = new Trend("chat_duration", true);
const planDuration = new Trend("plan_duration", true);
const authFailures = new Rate("auth_failures");
const chatFailures = new Rate("chat_failures");
const requestsTotal = new Counter("requests_total");

// ── Helper ─────────────────────────────────────────────────────

function randomString(length = 8): string {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let result = "";
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

// ── Main test ──────────────────────────────────────────────────

export default function () {
  const username = `k6_user_${randomString()}`;
  const password = "K6Test123";

  requestsTotal.add(1);

  // ── Registration & Login ──
  group("01_authentication", function () {
    // Register
    const registerRes = http.post(
      `${BASE_URL}/api/v1/auth/register`,
      JSON.stringify({ username, password, display_name: "K6 User" }),
      { headers: { "Content-Type": "application/json" } }
    );
    authDuration.add(registerRes.timings.duration);
    const registerOk = check(registerRes, {
      "register status is 201": (r) => r.status === 201,
      "register returns access_token": (r) => {
        try {
          return JSON.parse(r.body).access_token !== undefined;
        } catch {
          return false;
        }
      },
    });
    if (!registerOk) authFailures.add(1);

    // Login
    const loginRes = http.post(
      `${BASE_URL}/api/v1/auth/login`,
      JSON.stringify({ username, password }),
      { headers: { "Content-Type": "application/json" } }
    );
    authDuration.add(loginRes.timings.duration);
    const loginOk = check(loginRes, {
      "login status is 200": (r) => r.status === 200,
      "login returns access_token": (r) => {
        try {
          return JSON.parse(r.body).access_token !== undefined;
        } catch {
          return false;
        }
      },
    });
    if (!loginOk) authFailures.add(1);

    const token = loginOk ? JSON.parse(loginRes.body).access_token : "";
    const authHeaders = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    };

    // ── Chat ──
    group("02_chat", function () {
      const chatMessages = [
        "你好",
        "推荐一些健康饮食建议",
        "今天天气怎么样",
        "帮我规划一个北京三日游",
        "介绍一下你自己",
      ];

      for (const msg of chatMessages) {
        const chatRes = http.post(
          `${BASE_URL}/api/v1/chat`,
          JSON.stringify({ message: msg, session_id: `k6-session-${username}` }),
          { headers: authHeaders }
        );
        chatDuration.add(chatRes.timings.duration);
        const chatOk = check(chatRes, {
          "chat status is 200": (r) => r.status === 200,
          "chat returns message": (r) => {
            try {
              const body = JSON.parse(r.body);
              return body.message !== undefined && body.message.length > 0;
            } catch {
              return false;
            }
          },
        });
        if (!chatOk) chatFailures.add(1);

        // Brief pause between requests to simulate real user
        sleep(Math.random() * 2 + 1);
      }
    });

    // ── Profile ──
    group("03_profile", function () {
      const meRes = http.get(`${BASE_URL}/api/v1/users/me`, {
        headers: authHeaders,
      });
      check(meRes, {
        "profile status is 200": (r) => r.status === 200,
      });

      const prefsRes = http.put(
        `${BASE_URL}/api/v1/users/me/preferences`,
        JSON.stringify({ theme: "dark", language: "zh" }),
        { headers: authHeaders }
      );
      check(prefsRes, {
        "preferences update status is 200": (r) => r.status === 200,
      });
    });

    // ── Task runtime visibility ──
    group("04_runtime", function () {
      const tasksRes = http.get(`${BASE_URL}/api/v1/runtime/tasks`, {
        headers: authHeaders,
      });
      check(tasksRes, {
        "tasks list status is 200": (r) => r.status === 200,
      });
    });

    // ── Health checks ──
    group("05_health", function () {
      const healthRes = http.get(`${BASE_URL}/health`);
      check(healthRes, {
        "health endpoint ok": (r) => r.status === 200,
      });

      const readyRes = http.get(`${BASE_URL}/api/v1/health/ready`);
      check(readyRes, {
        "readiness endpoint ok": (r) => r.status === 200,
      });
    });
  });

  sleep(1);
}
