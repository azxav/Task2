# Measured extraction report

Selected: **Tev1 4B Q4_K_M + local PaddleOCR-VL-1.6**. Tev1 0.8B Q8_0 remains a faster measured option; Qwen3.5 4B is a text-only comparison. The production stack selects verbatim source candidates and validates evidence. Scans receive OCR first; decision models never receive images.

## Evaluation protocol

Twelve PDFs, six text/scanned families, eight pages per mode, **46 manually annotated obligations per mode**. Development: NAMUNA_1, NAMUNA_2, xat_1, xat_3 (30 tasks). Original held-out: NAMUNA_3 and xat_2 (16 tasks); pairs stayed together. Gold was checked against scan images before inference.

The original independent freeze/results are retained in `../production-freeze-v1.json` and `frozen-v1/`; classifier source is Git commit `486cbd0`. Its 4B held-out native results: 16/16 tasks, no extras, 8/8 metadata, no executor/deadline errors. Original scan results: 16/16 tasks, one duplicate introduction, 7/8 metadata, four executor and two deadline errors.

Inspection exposed generic parser gaps: deadline apostrophe variants, escaped OCR table line breaks, damaged document-number markers, merged organization/title blocks, and introductory requests containing referenced agreement dates. These were fixed with synthetic RED/GREEN regressions. **Revised test results below are exposed-set re-evaluation, not independent held-out accuracy.** The original independent results were not rewritten. No sample organization names/counts or gold values enter extraction rules; no OCR words were repaired from paired native PDFs.

Current freeze: `../production-freeze.json`, explicitly `test_set_exposed=true`. Raw OCR/weights remain unchanged; cached VL spans/cells were reparsed for known escaped-linebreak formatting with original capture hashes and raw output retained. Recognition timings refer to their original captures. Stack fingerprints normalize CRLF/LF for Git reproducibility; measured bytewise fingerprints are retained alongside canonical fingerprints. This metadata migration changed no inputs, predictions, metrics or timings.

## Revised stack comparison

Errors refer to matched tasks; executor errors compare the whole executor set. Metadata is four fields per PDF. These are **whole-stack scores**, including explicit-structure safeguards, not pure model accuracy.

| Split / input | Model | Matched / expected | Extras | Executor errors | Deadline errors | Metadata correct | Kind errors |
|---|---|---:|---:|---:|---:|---:|---:|
| Dev / native | Tev1 0.8B | 30/30 | 0 | 0 | 0 | 14/16 | 5 |
| Dev / native | **Tev1 4B** | **30/30** | **0** | **0** | **0** | **16/16** | **2** |
| Dev / native | Qwen 4B | 30/30 | 0 | 0 | 0 | 16/16 | 3 |
| Dev / OCR | Tev1 0.8B | 30/30 | 0 | 5 | 1 | 15/16 | 4 |
| Dev / OCR | **Tev1 4B** | **30/30** | **0** | **5** | **1** | **16/16** | **2** |
| Dev / OCR | Qwen 4B | 30/30 | 0 | 5 | 1 | 16/16 | 3 |
| Exposed test / native | Tev1 0.8B | 16/16 | 1 | 0 | 0 | 6/8 | 3 |
| Exposed test / native | **Tev1 4B** | **16/16** | **0** | **0** | **0** | **8/8** | **2** |
| Exposed test / native | Qwen 4B | 16/16 | 0 | 2 | 0 | 7/8 | 2 |
| Exposed test / OCR | Tev1 0.8B | 16/16 | 0 | 3 | 1 | 5/8 | 3 |
| Exposed test / OCR | **Tev1 4B** | **16/16** | **0** | **3** | **1** | **8/8** | **2** |
| Exposed test / OCR | Qwen 4B | 16/16 | 0 | 5 | 1 | 7/8 | 3 |

Selected 4B totals across the supplied set: native **46/46 tasks**, 24/24 metadata, 46/46 executor sets and deadlines; scans **46/46 tasks**, 24/24 metadata, **38/46 executor sets**, **44/46 deadlines**. No split/merge or extra-task errors in revised 4B outputs. Native instruction wording: 46/46 normalized exact; scans: 36/46. Kind labels: 42/46 correct in each mode. Successful task retrieval does not imply every field or category is correct.

Task matching uses greedy instruction similarity ≥0.65; exact field checks normalize case, apostrophe forms and whitespace, not spelling. Full matches and differences are in per-document records. Grouping was inspected against complete source/gold instructions; compound draft+submission and appendix execution+progress reporting remain single tasks.

## OCR selection

Critical coverage checks normalized exact sender/number/date/signer, executor and deadline strings in parsed OCR text. It measures source availability, not correct field assignment.

| OCR profile | Dev coverage | Original test coverage | Revised test coverage | Table rows recovered / 23 |
|---|---:|---:|---:|---:|
| PP-OCRv5 Latin, CPU | 51/76 | 26/38 | unchanged | 18/23 |
| Tesseract Uzbek+English, CPU | 62/76 | 27/38 | unchanged | 18/23 |
| **PaddleOCR-VL-1.6, GPU** | **70/76** | **34/38** | **35/38** | **23/23** |

VL was selected on development quality before final-test inspection. It preserved appendix tables which both CPU profiles failed to reconstruct in NAMUNA_3. Tesseract performed better on NAMUNA_1's plain paragraph scan (18/18 versus VL 17/18), so VL is not universally the best recognizer. Whole-table evidence boxes are flagged when exact cell geometry cannot be established; recovered row count does not prove perfect cell geometry.

Development VL layout-sensitive character error rates: 1.05%, 0.48%, 4.77%, 3.89% (NAMUNA_1, NAMUNA_2, xat_1, xat_3). This includes reading-order differences; it is not isolated character-recognition error. PPv5/Tesseract table reading-order differences inflate this metric. Raw blocks, confidences where supplied, source boxes, diagnostics and exact configuration hashes remain in OCR records.

## Remaining errors and review

All ten remaining 4B critical scan discrepancies come from OCR/source transcription after field-specific manual adjudication: damaged `martdan`, `muassasalarida`, unit names, a joined conditional-deadline phrase, and `Loyihaga` instead of `Loyiha` in executor cells. The correct coordinator phrase appears elsewhere in xat_2, so document-wide candidate availability initially misattributed that cell corruption to linking. See `manual-adjudication.json`; explicit row/cell evidence was preserved instead of borrowing another passage's wording.

Four kind-label errors remain per mode. These affect classification, not retention of the complete obligation. The error ledger preserves actual expected/predicted values. Original frozen failures and exploratory outputs are retained separately; suspended/aborted runs are excluded from final timing summaries.

Review reasons expose model/structure disagreement and layout ambiguity. They do **not** detect every plausible OCR word error: some development scan discrepancies had no automatic review flag. `supported` proves verbatim source grounding, not image transcription correctness. Verify original PDF pages before relying on extracted fields. Future quality work: independently evaluated OCR ensembles/recognition improvements and kind calibration on new families; no invented dates or corrected names.

## Runtime measurements

Windows, Python 3.12.10, 16 GB RAM, RTX 4050 laptop / 6 GB VRAM, Ollama 0.40.3. Tags/digests are pinned in `../../model-profiles.json`. Tev1 0.8B is 752.39M parameters Q8_0; both 4B profiles are 4.2B Q4_K_M. Quantization and runtime differ, so gains cannot be attributed solely to parameter count.

| Decision profile | Dev median native / OCR-text seconds | Peak GPU MiB | Dev native process-tree RSS GiB |
|---|---:|---:|---:|
| Tev1 0.8B | 6.5 / 5.1 | 965 | 5.85 |
| **Tev1 4B** | **16.8 / 16.3** | **2881** | **8.14** |
| Qwen 4B | 24.4 / 26.0 | 3751 | 8.61 |

These decision timings exclude OCR. Each model/mode starts cold on the first document; remaining documents are warm. Detailed cold/warm timings are in JSON. One-second resource samples include the owned Ollama server/runner; GPU is whole-device memory, RSS can include retained allocator/cache residency and is not pure weight size or total system RAM.

OCR development per-document durations: VL 68.6–137.4 s, Tesseract 5.1–12.2 s, PPv5 16.7–37.0 s. VL peak GPU **5913 MiB**, close to the laptop limit. App unloads dedicated Ollama weights before OCR; OCR worker exits before Tev1 loads. CPU VL was impractically slow and stopped; no fabricated CPU-VL score. GPU runs completed despite a compiled cuDNN 9.9 / installed 9.5 warning; exact environments/weights are locked. Windows sleep interrupted one comparison; its failed request was excluded and the complete run restarted. Temporary idle-sleep prevention was used only during measurements.

## Delivery and verification

`production/` contains all twelve actual 4B JSON results, with split labels, model digest, stack fingerprint, raw OCR provenance and decision traces. `summary.json`, `error-ledger.json`, OCR records and all three model comparisons provide auditable counts. Setup/limits/schema: `../../README.md`. Requirement and browser/visual audits: `../decision-stack-audit.md`, `../ui-qa.md`.

71 tests pass; ruff passes. Local inference runs with external TCP rejected in app/OCR Python processes, loopback-only model URLs and locally bundled assets. This is application-level isolation, not an OS firewall. Only six related document families were supplied; revised test families are exposed, and handwriting/Cyrillic/complex merged tables/other domains remain unvalidated.
