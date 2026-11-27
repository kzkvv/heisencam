import { spawnSync } from "node:child_process";
import { copyFileSync, readFileSync } from "node:fs";

const makefile = readFileSync(new URL("../../Makefile", import.meta.url), "utf8");
const release = makefile.match(/^VERSION\s*=\s*(\d+\.\d+\.\d+)\s*$/m)?.[1];
if (!release) {
  throw new Error("Expected VERSION in the root Makefile.");
}

// Keep the release schema alongside the generated API pages in the snapshot.
copyFileSync(
  ".generated/static/frigate-api.yaml",
  "docs/integrations/api/frigate-api.yaml",
);

const snapshot = spawnSync(
  process.execPath,
  ["node_modules/@docusaurus/core/bin/docusaurus.mjs", "docs:version", release],
  {
    env: { ...process.env, HEISENCAM_DOCS_PREVIEW: "1" },
    stdio: "inherit",
  },
);

if (snapshot.error) {
  throw snapshot.error;
}
process.exitCode = snapshot.status ?? 1;
