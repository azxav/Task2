# Evaluation references

Expected outputs were manually annotated before model inference or prompt tuning. All eight scanned pages were visually reviewed, including the body/footer distinction, unnumbered reporting obligations and appendix tables. Native-text extraction assisted verbatim transcription; it did not determine obligation labels, executor roles or deadline associations.

Six families contain 46 obligations (7, 8, 9, 7, 7, 8), present in both text and scanned versions. The initial table-establishing instruction is an approval obligation. The global deadline directive is also retained as an obligation. Recurring obligations remain single records. Compound actions remain together. Recipient references are resolved only where the letter explicitly addresses the requested action to that recipient; their evidence must include the address block. The appendix letter's compound execution/reporting paragraph remains one instruction; its recurring deadline qualifies reporting.

Four families are development data; two paired families are final-test data. The manifest fixes the split and source hashes bind annotations to the actual PDFs. No final-test examples may tune prompts, OCR choice, candidates or review thresholds. With only two held-out families, results are a small sample, not a general Uzbek-document accuracy guarantee.

Source archive: `Files Task_2.rar` provided by the user. Extract to `evaluation/source/` using `tar -xf <archive> -C evaluation/source`. Source PDFs are ignored; gold references, source hashes and measured results are versioned.
