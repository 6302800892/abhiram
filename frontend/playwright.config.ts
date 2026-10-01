import { defineConfig, devices } from "@playwright/test";
import os from "node:os";
import path from "node:path";

// The evaluator's Layer-2 checks: the real FastAPI backend serves the built portal (npm run build first).
// MEDICARD_PYTHON lets CI use `poetry run python`; locally the project venv is used.
const PORT = 8123;
const python =
  process.env.MEDICARD_PYTHON ??
  (process.platform === "win32" ? path.join(".venv", "Scripts", "python.exe") : "python3"); // relative to the repo root (webServer cwd)
const dbPath = process.env.MEDICARD_E2E_DB ?? path.join(os.tmpdir(), `medicard-e2e-${process.pid}.db`);

export default defineConfig({
  testDir: "./e2e",
  snapshotPathTemplate: "{testDir}/__snapshots__/{testFilePath}/{arg}{ext}",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.02 } },
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `"${python}" -m uvicorn src.main:create_app --factory --host 127.0.0.1 --port ${PORT}`,
    cwd: "..",
    url: `http://127.0.0.1:${PORT}/health`,
    reuseExistingServer: false,
    stdout: "ignore",
    stderr: "pipe",
    timeout: 60_000,
    env: {
      MEDICARD_DB_PATH: dbPath,
      MEDICARD_FRONTEND_DIST: path.resolve("dist"),
      MEDICARD_PBKDF2_ITERATIONS: "1000",
      MEDICARD_SECRET: "e2e-only-secret-not-for-production",
    },
  },
});
