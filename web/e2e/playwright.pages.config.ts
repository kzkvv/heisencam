import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

const prefix = process.env.HEISENCAM_PAGES_BASE || "";
const port = 18797;

export default defineConfig({
  testDir: "./pages",
  use: {
    channel: "chrome",
    baseURL: `http://127.0.0.1:${port}${prefix}/`,
    viewport: { width: 1440, height: 900 },
  },
  webServer: {
    cwd: fileURLToPath(new URL("..", import.meta.url)),
    command: `python3 ../tools/serve_docs_pages.py --port ${port} --prefix '${prefix}'`,
    url: `http://127.0.0.1:${port}${prefix}/demo/`,
    reuseExistingServer: false,
  },
});
