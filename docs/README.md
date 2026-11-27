# Documentation and public site

The [documentation](https://docs.heisen.cam/) uses Docusaurus. The [browser demo](https://docs.heisen.cam/demo/) plays recorded street scenes and sample detections without an account.

## Build

Use Node.js 24 and npm. Run these commands from the repository root.

```sh
cd docs
npm ci
npm run build
```

The build checks internal links and generates the HTTP API reference from `docs/static/frigate-api.yaml`. GitHub Actions publishes this build at the root of `docs.heisen.cam` with the app built from the same commit under `/demo/` and redirects from the previous `/docs/` paths.

Run `npm run start` from `docs/` to preview the documentation locally. The `HEISENCAM_DOCS_URL` environment variable sets the public origin and base path for a different deployment.

To reproduce the Pages artifact and run the browser smoke test, build the documentation first and then run the following commands from the root.

```sh
cd web
npm ci
HEISENCAM_DEMO_BASE=/demo/ npm run build:demo
cd ..
python3 tools/prepare_docs_pages.py docs/build
cd web
npx playwright install chrome
npx playwright test --config e2e/playwright.pages.config.ts
```

The workflow packages the docs, sample media and source revision metadata. A release operator can run the documentation workflow on `dev` from GitHub Actions to rebuild and verify the Pages deployment.
