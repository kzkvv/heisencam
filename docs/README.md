# Documentation and public site

The [documentation](https://kzkvv.github.io/heisencam/docs/) uses Docusaurus. The [browser demo](https://kzkvv.github.io/heisencam/demo/) is a static, read-only player for the source media in `examples/demo/media`. The project site, demo and documentation share one GitHub Pages repository.

## Build

Use Node.js 24, npm and Python 3. Run these commands from the repository root.

```sh
cd docs
npm ci
npm run build
cd ..
python3 tools/build_public_site.py /tmp/heisencam-pages
```

The packaging command expects an empty or new output directory. It assembles the landing page, six selected recordings, their demo assets and the compiled documentation. Publish that directory at `/heisencam/` through the fork's `gh-pages` branch. The documentation build checks internal links and generates the HTTP API reference from `docs/static/frigate-api.yaml`.
