import { defineConfig } from "@playwright/test";
import config from "./playwright.config";

const baseURL = process.env.FRIGATE_PERF_URL;
const executablePath = process.env.FRIGATE_PERF_BROWSER;

export default defineConfig({
  ...config,
  testDir: "./performance",
  testMatch: "*.spec.ts",
  outputDir: "./performance/test-results",
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  webServer: baseURL ? undefined : config.webServer,
  use: {
    ...config.use,
    baseURL: baseURL || config.use?.baseURL,
    serviceWorkers: "block",
    trace: "retain-on-failure",
    launchOptions: executablePath ? { executablePath } : undefined,
  },
  projects: config.projects?.filter((project) => project.name === "desktop"),
});
