import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command:
        "cd .. && uv run python scripts/seed_e2e_db.py && uv run uvicorn ai_commerce_gateway.api.app:app --port 8000",
      url: "http://127.0.0.1:8000/health/live",
      reuseExistingServer: false,
      timeout: 120000,
      env: {
        APP_ENV: "test",
        DATABASE_URL: "sqlite:///e2e_test.db",
        BUYER_SESSIONS_ISSUER_KEY: "dev-issuer-key",
        BUYER_SESSIONS_SECRET: "test-session-secret",
        RAZORPAY_KEY_ID: "rzp_test_fake123",
        RAZORPAY_KEY_SECRET: "fake_secret",
      },
    },
    {
      command: "npm run dev -- -p 3000",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: false,
      timeout: 120000,
      env: {
        APP_ENV: "test",
        BACKEND_ORIGIN: "http://127.0.0.1:8000",
        BUYER_SESSIONS_ISSUER_KEY: "dev-issuer-key",
        E2E_BUYER_ID: "buyer_1",
      },
    },
  ],
});
