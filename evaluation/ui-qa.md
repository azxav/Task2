# Browser and visual QA

Actual localhost app launched with `./run.ps1`, API 8132, dedicated Ollama 11435. Manually exercised through Codex in-app browser; screenshots are browser captures, not mock results.

## Functional evidence

- Native paragraph NAMUNA_1: seven complete tasks; draft development + Council submission stays one; two executors survive; recurring and inherited deadlines retain original wording. Final downloaded JSON compared against gold: 7/7 tasks, 4/4 metadata, zero executor/deadline/kind errors.
- Native table NAMUNA_2: eight tasks, metadata and all assigned fields checked; unspecified cells displayed as Ko‘rsatilmagan. Actual downloaded JSON matched gold.
- Scanned appendix NAMUNA_3: actual browser → API → GPU OCR → text-only Tev1 → nine tasks → JSON export. Downloaded result: 9/9 tasks, 4/4 metadata, zero extras, one executor and one deadline OCR discrepancy. Both pages explicitly recorded as OCR. Page-two source button opened the original appendix table; local preview survived server upload cleanup.
- Evidence expanded via pointer and Enter; keyboard focus outline visible. JSON values matched displayed strings; populated fields cite actual source IDs.
- Invalid/corrupt PDF returned 422, visible error, unlocked form and empty upload directory. Automated checks also cover concurrency, disconnect, storage and inference failures, encryption and size/page limits.
- A final replacement check reproduced PDF.js 6 removing `PDFDocumentProxy.destroy()`. Changed cleanup to its `loadingTask.destroy()` and retested replacing a rendered PDF without reload. Old result/download state resets with selection.
- Final narrow scan result: clientWidth=scrollWidth=360, no horizontal overflow. Earlier 375px check also passed. Temporary viewport overrides reset after QA.
- Browser errors from the reproduced lifecycle failure retained during diagnosis; subsequent replacement checks verified no new error. Models/assets remain local; external TCP probe rejected before connection. Server upload directory empty after completed jobs.

## Visual comparison

Accepted reference: [design-concept.png](screenshots/design-concept.png). Wide native implementation: [native-final.png](screenshots/native-final.png), [desktop.png](screenshots/desktop.png). Scan evidence: [appendix-page2.png](screenshots/appendix-page2.png), [scan-result.png](screenshots/scan-result.png). Narrow layout: [mobile-scan.png](screenshots/mobile-scan.png), [mobile.png](screenshots/mobile.png). Error state: [invalid-input.png](screenshots/invalid-input.png).

Concept and real captures inspected side by side at the native wide reference viewport, plus narrow captures. Five fidelity checks: warm off-white/grid and black borders; heavy black heading/monospace labels; lime analysis action; two-column panel proportions and spacing; upload/download/source controls and readable body text. Header/title and empty-state copy preserved. Dynamic filename, task counts, metadata, review notices and pagination are intentional functional additions. Local canvas PDF.js/page controls replace the concept's static preview, fixing blank embedded PDF behavior. Native font rendering and practical result expansion differ slightly from the raster concept; no material layout mismatch identified.

## Limits

This proves representative workflows, not all documents/browsers. OCR errors remain even with source grounding; review flags do not detect every corrupted word. Browser evidence complements all twelve measured production outputs and 71 passing backend tests; it is not an independent accuracy evaluation.
