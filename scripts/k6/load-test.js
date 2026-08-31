import http from "k6/http";
import { check, sleep, group } from "k6";
import { Trend, Rate } from "k6/metrics";

const httpRequestDuration = new Trend("http_req_duration_custom");
const errorRate = new Rate("errors");

export const options = {
  stages: [
    { duration: "30s", target: 10 },
    { duration: "1m", target: 10 },
    { duration: "30s", target: 50 },
    { duration: "1m", target: 50 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<500"],
    "http_req_failed": ["rate<0.05"],
    "errors": ["rate<0.05"],
  },
  tags: {
    test_run: "load-test",
    environment: __ENV.E2E_BASE_URL ? "e2e" : "dev",
  },
};

const BASE_URL = __ENV.EUIE_BASE_URL || __ENV.BASE_URL || "http://localhost:8009";

export default function () {
  // === Root page ===
  let res = http.get(`${BASE_URL}/`);
  check(res, {
    "root page status is 200": (r) => r.status === 200,
  });
  httpRequestDuration.add(res.timings.duration);
  errorRate.add(res.status !== 200);

  // === Health check ===
  res = http.get(`${BASE_URL}/health/`);
  check(res, {
    "health check status is 200": (r) => r.status === 200,
  });

  // === Login page ===
  res = http.get(`${BASE_URL}/accounts/login/`);
  check(res, {
    "login page status is 200": (r) => r.status === 200,
  });

  // === Public API endpoints ===
  res = http.get(`${BASE_URL}/api/openapi.json`);
  check(res, {
    "openapi schema status is 200": (r) => r.status === 200,
  });

  sleep(1);
}
