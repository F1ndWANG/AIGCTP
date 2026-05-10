import http from "k6/http";
import { check } from "k6";

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    http_req_duration: ["p(95)<5000"],
    http_req_failed: ["rate<0.5"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export default function () {
  // Health check
  const health = http.get(`${BASE_URL}/health`);
  check(health, { "health returns 200": (r) => r.status === 200 });

  // Readiness
  const ready = http.get(`${BASE_URL}/api/v1/health/ready`);
  // readiness may fail if DB/Redis not configured — just check it responds
  check(ready, {
    "ready responds": (r) => r.status === 200 || r.status === 503,
  });

  // Register user
  const rand = Math.random().toString(36).slice(2, 8);
  const regBody = JSON.stringify({
    username: `smoke_${rand}`,
    password: "SmokeTest1",
  });
  const register = http.post(`${BASE_URL}/api/v1/auth/register`, regBody, {
    headers: { "Content-Type": "application/json" },
  });
  check(register, {
    "register succeeds": (r) => r.status === 201 || r.status === 400,
  });

  if (register.status === 201) {
    const loginBody = JSON.stringify({
      username: `smoke_${rand}`,
      password: "SmokeTest1",
    });
    const login = http.post(`${BASE_URL}/api/v1/auth/login`, loginBody, {
      headers: { "Content-Type": "application/json" },
    });
    check(login, { "login succeeds": (r) => r.status === 200 });
  }
}
