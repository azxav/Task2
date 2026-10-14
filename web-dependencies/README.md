# Local PDF preview

Bundled Mozilla PDF.js **6.4.299** (Apache-2.0), legacy ESM build. `package-lock.json` pins registry integrity. Only local `/assets/vendor/pdfjs/` modules, worker, fonts, CMaps and WASM are requested; no CDN or remote fonts. Original PDF bytes remain in the browser after server cleanup.

The native browser PDF iframe was blank during actual IAB testing. Canvas rendering, page controls and source-page navigation replace that unsupported preview.

To regenerate the bundle, run `npm ci --ignore-scripts` here, then copy `node_modules/pdfjs-dist/legacy/build/{pdf.mjs,pdf.worker.mjs}`, `LICENSE`, `cmaps/`, `standard_fonts/`, `wasm/` into `src/doc_tasks/web/vendor/pdfjs/`. Preserve upstream licenses.

[Official rendering API examples](https://mozilla.github.io/pdf.js/examples/).
