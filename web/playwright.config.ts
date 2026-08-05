import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:4321",
    locale: "de-DE",
    trace: "retain-on-failure",
    ...devices["Desktop Chrome"],
  },
  webServer: {
    command: "npm run build && npm run preview -- --host 127.0.0.1 --port 4321",
    url: "http://127.0.0.1:4321/",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
