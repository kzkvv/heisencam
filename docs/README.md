# Documentation and public site

The [documentation](https://docs.heisen.cam/) uses Docusaurus. The [browser demo](https://docs.heisen.cam/demo/) plays recorded street scenes and sample detections without an account.

## Build

Use Node.js 24 and npm. Run these commands from the repository root.

```sh
cd docs
npm ci
npm run build
```

The build checks internal links and generates the HTTP API reference from `docs/static/frigate-api.yaml`. GitHub Actions publishes this build at the root of `docs.heisen.cam` with the published browser demo under `/demo/` and redirects from the previous `/docs/` paths.

Run `npm run start` from `docs/` to preview the documentation locally. The `HEISENCAM_DOCS_URL` environment variable sets the public origin and base path for a different deployment.
