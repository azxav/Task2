"""Build delivery summaries from measured records; never infer missing measurements."""
import json
from collections import defaultdict
from statistics import median

from doc_tasks.benchmark import ROOT, code_hash
from doc_tasks.candidates import generate_candidates
from doc_tasks.evaluate import normalize
from doc_tasks.schema import Document

RESULTS = ROOT / "evaluation/results"


def main():
    groups = defaultdict(list)
    errors = []
    production = RESULTS / "production"
    production.mkdir(exist_ok=True)
    profiles = json.loads((ROOT / "model-profiles.json").read_text(encoding="utf-8"))["models"]
    for split in ("dev", "test"):
        for mode in ("native", "ocr"):
            for path in (RESULTS / f"{split}-{mode}-final").glob("*--*.json"):
                record = json.loads(path.read_text(encoding="utf-8"))
                if record["code_sha256"] != code_hash():
                    raise ValueError(f"Stale stack record: {path.name}")
                groups[(split, mode, record["model"])].append(record)
                gold = json.loads((ROOT / "evaluation/gold" / (record["document"] + ".json")).read_text(encoding="utf-8"))
                analysis = record["analysis"]
                if mode == "ocr":
                    capture = json.loads((RESULTS / f"{split}-ocr-paddle-vl" / (record["document"] + ".json")).read_text(encoding="utf-8"))
                    doc = Document.model_validate(capture["document"])
                else:
                    doc = Document(spans=analysis["sources"], passages=[])
                source = normalize(" ".join(s.text for s in doc.spans))
                candidates = {normalize(c.text) for c in generate_candidates(doc)} if mode == "ocr" else None

                def error(field, expected, actual, task=None, source=source, split=split,
                          mode=mode, record=record, candidates=candidates):
                    values = expected if isinstance(expected, list) else [expected]
                    present = all(v is None or normalize(v) in source for v in values)
                    errors.append({"split": split, "mode": mode, "model": record["model"],
                                   "document": record["document"], "field": field, "task_index": task,
                                   "expected": expected, "actual": actual, "gold_text_in_source": present,
                                   "gold_candidate_available": None if candidates is None else all(
                                       v is None or normalize(v) in candidates for v in values),
                                   "attribution": "OCR/source transcription" if not present else "decision/candidate/linking"})

                for role, correct in record["metrics"]["metadata"].items():
                    if not correct:
                        error(role, gold["metadata"][role]["text"], analysis["metadata"][role]["text"])
                for match in record["metrics"]["matched_details"]:
                    gi, pi = match["gold_index"], match["prediction_index"]
                    expected, actual = gold["tasks"][gi], analysis["tasks"][pi]
                    if match["executor_wrong"]:
                        error("executors", expected["executors"], [v["text"] for v in actual["executors"]], gi)
                    if match["deadline_wrong"]:
                        error("deadline", expected["deadline"], actual["deadline"]["text"], gi)
                    if match["kind_wrong"]:
                        errors.append({"split": split, "mode": mode, "model": record["model"],
                                       "document": record["document"], "field": "kinds", "task_index": gi,
                                       "expected": expected["kinds"], "actual": actual["kinds"],
                                       "attribution": "decision classification"})
                if record["model"] == "tev1:4b-q4_K_M":
                    analysis["provenance"].update(stack_sha256=record["code_sha256"], split=split,
                        model_digest=profiles[record["model"]]["digest"], decision_trace=record["decisions"])
                    (production / (record["document"] + ".json")).write_text(
                        json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    keys = ["expected_tasks", "predicted_tasks", "matched_tasks", "missed_tasks", "spurious_tasks",
            "executor_errors", "deadline_errors", "instruction_wording_errors", "kind_errors",
            "metadata_correct", "metadata_fields", "grouping_errors", "review_tasks"]
    summary = []
    for (split, mode, model), records in sorted(groups.items()):
        totals = {key: sum(r["metrics"][key] for r in records) for key in keys}
        totals.update(split=split, mode=mode, model=model, documents=len(records),
                      median_decision_seconds=median(r["seconds"] for r in records),
                      cold_seconds=next(r["seconds"] for r in records if r["load_state"] == "cold"),
                      peak_gpu_mib=max(r["peak_gpu_memory_mib"] for r in records),
                      peak_rss_bytes=max(r["peak_process_tree_rss_bytes"] for r in records))
        summary.append(totals)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (RESULTS / "error-ledger.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in summary:
        print(row["split"], row["mode"], row["model"], {k: row[k] for k in
              ["matched_tasks", "missed_tasks", "spurious_tasks", "executor_errors", "deadline_errors", "metadata_correct", "kind_errors"]})
    if len(summary) == 12 and len(list(production.glob("*.json"))) == 12:
        print("All twelve production outputs and twelve split/mode/model summaries present")


if __name__ == "__main__":
    main()
