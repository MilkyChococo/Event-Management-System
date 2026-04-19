// @ts-check
const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests/e2e",
  testMatch: /lab2-review\.spec\.js$/,
  timeout: 60000,
  expect: {
    timeout: 10000,
  },
  fullyParallel: false,
  workers: 1,
  reporter: [["html", { open: "never", outputFolder: "playwright-report/lab2" }], ["list"]],
  use: {
    baseURL: "http://127.0.0.1:10104",
    trace: "on-first-retry",
  },
  webServer: {
    command: "powershell -ExecutionPolicy Bypass -File scripts\\run_lab2_server.ps1",
    port: 10104,
    timeout: 120000,
    reuseExistingServer: true,
  },
});
