"""Reapply passage rules to unchanged cached VL spans/cells, without redoing OCR."""
import argparse
import json
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from doc_tasks.benchmark import code_hash, input_hash
from doc_tasks.evaluate import normalize
from doc_tasks.ocr import NoOCR, OCRPage, TableRow
from doc_tasks.pdf import read_pdf
from doc_tasks.schema import Document
from doc_tasks.structure import build_passages


def rebuild(path, allow_exposed_test=False):
    record = json.loads(path.read_text(encoding="utf-8"))
    document = Document.model_validate(record["document"])
    if record["split"] != "dev":
        protocol = json.loads((path.parents[2] / "production-freeze.json").read_text(encoding="utf-8"))
        if not allow_exposed_test or not protocol.get("test_set_exposed"):
            raise ValueError("Test cache normalization requires explicit exposed-test protocol")
    raw_pages = document.provenance["ocr_raw_results"]
    pages = []
    table_refs = {ref for passage in document.passages if passage.kind == "table_row"
                  for ref in passage.span_ids}
    original_text = {span.id: span.text for span in document.spans}
    for span in document.spans:
        if span.id in table_refs:
            span.text = " ".join(span.text.replace("\\n", " ").split())
    for number in sorted({span.page for span in document.spans}):
        raw = raw_pages[str(number)]
        spans = [span for span in document.spans if span.page == number]
        ids = {span.id for span in spans}
        rows = [TableRow(id=p.id, reference=p.clause_ref, cells=p.table_cells)
                for p in document.passages if p.kind == "table_row" and p.span_ids[0] in ids]
        pages.append(OCRPage(page=number, width=raw["width"], height=raw["height"], spans=spans,
                             rows=rows, raw_result=raw))
    rebuilt = build_passages(pages)
    rebuilt.warnings = list(dict.fromkeys([*document.warnings, *rebuilt.warnings]))
    rebuilt.provenance = document.provenance
    assert rebuilt.spans == document.spans
    record["format_normalized_span_ids"] = [s.id for s in document.spans if s.text != original_text[s.id]]
    record["ocr_capture_code_sha256"] = record.get("ocr_capture_code_sha256", record["code_sha256"])
    record["code_sha256"] = code_hash()
    record["document"] = rebuilt.model_dump()
    record["input_sha256"] = input_hash(record["document"])
    record["passage_rebuild_note"] = "Current grouping and escaped table-linebreak formatting applied; raw OCR/weights/word predictions unchanged. Recognition timing remains original capture timing."
    root = path.parents[2]
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    item = next(i for i in manifest["documents"] if i["id"] == path.stem)
    reference = next(i for i in manifest["documents"] if i["family"] == item["family"] and not i["scanned"])
    expected = normalize(" ".join(s.text for s in read_pdf(root / reference["path"], NoOCR()).spans))
    actual = normalize(" ".join(s.text for s in rebuilt.spans))
    record["layout_sensitive_cer"] = Levenshtein.distance(expected, actual) / max(1, len(expected))
    gold = json.loads((root / item["gold"]).read_text(encoding="utf-8"))
    critical = [v["text"] for v in gold["metadata"].values()] + [v for t in gold["tasks"]
                for v in [*t["executors"], t["deadline"]] if v]
    record["critical_exact_present"] = sum(normalize(v) in actual for v in critical)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--allow-exposed-test", action="store_true")
    args = parser.parse_args()
    for path in args.directory.glob("*.json"):
        rebuild(path.resolve(), args.allow_exposed_test)
