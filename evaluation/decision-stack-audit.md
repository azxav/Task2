# Decision-stack requirement audit

The supplied document families drive the stack: decision rules contain no sample organization names, expected task counts or gold outputs. Production inference consumes the uploaded PDF only; paired native documents and gold are evaluation references, never OCR correction inputs.

| Requirement | Implementation / evidence |
|---|---|
| All obligation types, including approval and oversight | Independent presence and kind decisions; explicit row/action retention; `test_extract.py`, table/inheritance tests, per-document measured results |
| Develop draft + submit Council remains one task | Same-draft protection and contextual boundary classification; adversarial boundary regression |
| Distinct obligations stay separate | Source-literal segmentation; independent executor/deadline pools; distinct executor/deadline regression |
| No guessed/calculated time | Verbatim date/deadline candidates; unknown choice; conditional/recurring/working-day tests; no date arithmetic |
| Executor versus recipient/preparer/signer | Independent responsibility questions; explicit subject/cell rules; footer exclusion; multi-executor and cooperation regressions |
| Multipage signatures and wrapped/continuation obligations | Whole-block action guard; all-page signature candidates; six final review regressions |
| OCR before Tev1/Qwen on scans | Page-mode provenance and mixed-PDF tests; workers emit text/cells; inference payloads contain no images |
| Ambiguity visible | `needs_review`, source/model disagreement reasons, unknown candidate tests; probabilities not presented as accuracy |
| Evidence for every fact | Pydantic reference validation, verbatim grounding, parent spans, inherited task + directive references |
| Tev1 primary; 0.8B compared | Pinned digests; production refuses Qwen; same serialized input hashes across three-model comparisons |
| Local operation | Loopback-only inference URL, proxy bypass, external TCP rejection in app/OCR processes; locally bundled PDF.js/assets; no online inference fallback |
| Limits and cleanup | 20 MB/20 pages, encrypted/corrupt rejection, concurrent 409, disconnect/failure cleanup, storage-failure lock regression |
| Honest evaluation | Original independent v1 freeze/results retained; revised v2 test explicitly exposed; canonical CRLF/LF fingerprints retain measured bytewise hashes; all 36 comparisons use shared inputs |

Independent read-only review identified header omission, signer reachability and missing segmentation, then caught wrapped-prefix and consultation-role edge cases. Each was reproduced with controlled decisions, observed failing, fixed and verified. Implementation/manual annotation remained with the main agent.

The test suite has 71 passing tests; ruff passes. See `results/report.md` for actual inference quality, including failures. A structural safeguard is part of the measured stack; successful extraction does not prove Tev1 made every decision correctly.

Known boundaries: subject recognition is conservative Uzbek Latin syntax, not a full parser. Boundary decisions and default scope can still be wrong; difficult mixed assignments need human source review. Signer candidates exclude assigned clauses/tables/footer; signatures embedded within those structures are unvalidated. OCR may silently corrupt a critical token; grounding cannot detect that. Complex merged tables, handwriting, Cyrillic and unrelated document domains are not established by six example families.

Final artifact audit: all 36 current comparisons match the frozen canonical stack; three models share each document input hash; all twelve production results pass schema, parent-reference and verbatim grounding checks. Actual browser native paragraph: 7/7 tasks, 4/4 metadata, no executor/deadline errors. Actual browser scanned appendix: 9/9 tasks, 4/4 metadata, one executor and one deadline OCR error, no extras. UI lifecycle fixes do not change measured classifier fingerprints.
