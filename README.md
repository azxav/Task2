# Local document obligations — Task 2

> Full step-by-step explanation: [GUIDE.md](GUIDE.md).

Tev1 selects source-grounded facts from Uzbek official PDFs. Native PDF text stays native; scanned pages go through local OCR before text-only Tev1 decisions. Production: **Tev1 4B Q4_K_M + PaddleOCR-VL-1.6**. The 0.8B Q8_0 model and text-only Qwen3.5 4B are measured comparisons.

## Run on this prepared laptop

From this repository's root, in PowerShell:

```powershell
./run.ps1
```

Open [localhost:8132](http://127.0.0.1:8132/). Select PDF → **Tahlil qilish** → inspect tasks and source pages → **JSON yuklab olish**. Browser keeps the original PDF preview after server temporary files are deleted. Stop the web server with Ctrl+C. The dedicated local Ollama helper remains available on port 11435; its PID is recorded in `.cache/runtime/ollama.pid`.

```powershell
uv run doc-tasks health
uv run doc-tasks analyze 'document.pdf' --output 'result.json'
uv run pytest -q
uv run ruff check .
```

Application dependencies use `uv.lock` and their own Python 3.12 environment. CLI analysis writes only the output explicitly requested; the web API does not persist PDFs or results.

## Decision stack

1. Validate PDF size, page count, corruption and encryption. Read coordinate-aware native text; OCR image-only pages at 220 dpi.
2. Preserve paragraphs, numbered clauses, appendix tables, cell roles and source coordinates. Distinguish letterhead, signer and footer preparer. Continuation-page obligations remain eligible.
3. Consider literal task boundaries. Tev1 classifies independent obligations versus compounds; distinct explicit executor assignments remain separate, with review on disagreement. Develop-and-submit the same draft stays one task. Split spans retain parent references.
4. Generate broad verbatim candidates for sender, issue number/date, signer, executors and deadlines. Scope table fields to their own row/cell. Larger candidate sets use bounded tournaments rather than truncation.
5. Ask narrow Tev1 questions: obligation present, obligation kind, candidate responsibility, deadline relationship and explicit default applicability. Reject unsupported choices. Preserve explicit rows/actions on model disagreement and flag review.
6. Assemble copied text, source IDs/page evidence and review reasons. Verify evidence references and verbatim grounding. Include accepted/rejected decisions and pinned model/stack provenance in JSON.

Execution, approval, oversight, reporting and other explicit obligations count. Multiple executors survive. Original relative, recurring, working-day and conditional deadlines survive; dates are never calculated. Default deadlines require a separate scope decision and cite both the task and directive. Signers and footer `Ijrochi` preparers become executors only when explicitly assigned in the instruction.

`supported` means source-grounded, **not guaranteed correct**. `not_specified` has no asserted value. `needs_review` records ambiguous linking or explicit source/model disagreement. Tev1 concentration values are not calibrated correctness probabilities. OCR can produce plausible corrupted words without a warning; source review remains necessary.

## Local runtime and configuration

Tested: Windows, Python 3.12.10, Ollama **0.40.3**, NVIDIA RTX 4050 laptop / 6 GB VRAM, 16 GB RAM. Exact tags, weight digests and quantizations: [model-profiles.json](model-profiles.json). Runtime model digest is checked before analysis; changed or unbenchmarked weights are refused. Qwen cannot replace production Tev1 silently.

Setup on another machine requires downloads; analysis uses already downloaded files:

```powershell
uv sync --frozen --extra dev
$env:OLLAMA_HOST = '127.0.0.1:11435'
$env:OLLAMA_MODELS = Join-Path (Get-Location) '.cache/ollama-models'
# In the tested Ollama installation:
ollama pull tev1:4b-q4_K_M
ollama pull tev1:0.8b-q8_0
ollama pull qwen3.5:4b
```

Use the tested portable Windows [Ollama release](https://github.com/ollama/ollama/releases/tag/v0.40.3), including its CUDA runtime, under `.cache/runtime/ollama/` for `run.ps1`. Compare installed digests with `model-profiles.json` after pulling; mutable upstream tags can change. Full model settings and packaged Apache-2.0 licenses are captured in benchmark `runtime.json`. Tev1 uses `/v1/systemone`; Qwen comparison uses `/api/chat`, temperature 0, context 4096, thinking disabled, enum-constrained JSON and no images.

OCR setup, exact package locks, local weight hashes, model directories and CUDA compatibility caveat: [ocr-runtime/README.md](ocr-runtime/README.md). GPU OCR consumes nearly the whole 6 GB device. The app unloads its dedicated Ollama weights before OCR; the worker exits before Tev1 loads. Run benchmarks sequentially and unload any loaded comparison model before `benchmark-ocr`. CPU Tesseract/PPv5 profiles are explicitly configurable, never automatic fallback.

Optional environment settings (see [.env.example](.env.example)):

| Variable | Default |
|---|---|
| `DOC_TASKS_MODEL` | `tev1:4b-q4_K_M` |
| `DOC_TASKS_OLLAMA_URL` | `http://127.0.0.1:11435` |
| `DOC_TASKS_OCR` | `paddle-vl` |

PowerShell does not load `.env` automatically; set `$env:NAME` before starting. `run.ps1` disables Ollama cloud and Hugging Face online lookup, sets one loaded model and one inference slot. Application and OCR worker reject external TCP connections in their own Python processes; inference URL must be loopback. Assets, PDF.js worker, fonts and PDF data remain local. This is application-level isolation, not an operating-system firewall or a claim about unrelated programs.

## Limits and API

One PDF/job at a time; 20 MB, 20 pages. Encrypted PDFs unsupported. Layout reconstruction targets printed Uzbek Latin official documents resembling the supplied paragraphs, ruled tables and appendices. Handwriting, Cyrillic, complex merged tables, heavily damaged scans and other document domains are unvalidated.

| Route/result | Meaning |
|---|---|
| `POST /api/analyze` | multipart field `file`; `AnalysisResult` JSON |
| `GET /api/status` | busy + stage, no document text |
| `GET /api/health` | selected local model/OCR availability |
| 409 | another job running |
| 413 | size/page limit |
| 422 | invalid/encrypted PDF |
| 503 | unavailable local model/OCR/storage |

Worker owns cleanup/lock after browser disconnect. Marked stale job directories are removed at startup. Browser DOM uses text nodes for source content. Results contain four metadata fields; tasks have instruction, kinds, executors, deadline, clause reference and review reasons; each populated field cites `sources`, including page, bounding box and optional parent ID. Browser shows page evidence; editing and Excel export remain future scope.

## Evaluation and deliverables

Manually checked gold covers all twelve supplied PDFs (six text/scanned pairs, 46 obligations per mode). Four families are development; NAMUNA_3 and xat_2 were originally held out together with scans. Original independent results/source freeze remain in `evaluation/results/frozen-v1/` and `production-freeze-v1.json`. Later generic fixes used test feedback: current v2 results explicitly mark these families exposed, never independent validation. No sample organization names, task counts or expected predictions are embedded in extraction rules.

Put the original `Files Task_2` archive's `matnli/` and `skaner/` directories under `evaluation/source/Files Task_2/`; paths are recorded in [manifest.json](evaluation/manifest.json). Raw PDFs and multi-GB model caches are ignored; gold, configurations, measured output and decision traces are deliverables.

```powershell
uv run doc-tasks benchmark-ocr --engine paddle-vl --split dev
uv run doc-tasks compare --mode native --split dev
uv run doc-tasks compare --mode ocr --split dev
# Only after development selection; creates immutable protocol marker:
uv run doc-tasks freeze
uv run doc-tasks benchmark-ocr --engine paddle-vl --split test
uv run doc-tasks compare --mode native --split test
uv run doc-tasks compare --mode ocr --split test
```

See [measured report](evaluation/results/report.md), [decision-stack audit](evaluation/decision-stack-audit.md) and [browser/visual QA](evaluation/ui-qa.md). Comparisons measure the **whole decision stack**, including structural safeguards; they are not pure model accuracy or general Uzbek language benchmarks. Only two original held-out families limit generalization; new independent documents are needed to validate v2. Fingerprints normalize CRLF/LF; original bytewise fingerprints remain recorded.
