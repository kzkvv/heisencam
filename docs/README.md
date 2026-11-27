# Documentation and public site

The [documentation](https://docs.heisen.cam/) uses Docusaurus. The [browser demo](https://docs.heisen.cam/demo/) plays recorded street scenes and sample detections without an account.

## Build

Use Node.js 24 and npm. Run these commands from the repository root.

```sh
cd docs
npm ci
npm run build
```

The build checks internal links. GitHub Actions publishes the latest release at the root of `docs.heisen.cam`, older releases under `/<version>/`, and the browser demo under `/demo/`. The previous `/docs/` paths redirect to the corresponding documentation.

## Preview

Run `npm run start` from `docs/` to open the release and the working copy at `/next/`. Set `HEISENCAM_DOCS_PREVIEW=1` to include the working copy in a static build. The `HEISENCAM_DOCS_URL` environment variable sets the origin and base path.

## Release a documentation version

Update the guides in `docs/docs/` and the API schema in `docs/static/frigate-api.yaml` for the upcoming release. Keep version-specific data and images beside the guide that uses them, and link to other guides by their Markdown file paths.

From `docs/`, run `npm run snapshot` when the release is ready. It reads `VERSION` from the root `Makefile`, generates the Docker Compose settings and API reference, and copies the documentation, data, API schema, and sidebar into versioned files. Commit the resulting `versions.json` and the new directories and sidebar under `versioned_docs/` and `versioned_sidebars/`.
