"""Migrate recorded fingerprint representation; keep original bytewise fingerprint.

No input, model settings, decisions, metrics or timings are modified. The original
independent v1 protocol/results remain untouched.
"""
import json

from doc_tasks.benchmark import ROOT, code_hash


def main():
    bytewise, canonical = code_hash(normalize_line_endings=False), code_hash()
    paths = [ROOT / "evaluation/production-freeze.json"]
    results = ROOT / "evaluation/results"
    for name in ("dev-native-final", "dev-ocr-final", "test-native-final", "test-ocr-final",
                 "dev-ocr-paddle-vl", "test-ocr-paddle-vl"):
        paths.extend((results / name).glob("*.json"))
    changed = 0
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        if "code_sha256" not in record:
            continue
        if record["code_sha256"] == canonical:
            continue
        if record["code_sha256"] != bytewise:
            raise ValueError(f"Cannot re-label different classifier source: {path}")
        record["recorded_bytewise_code_sha256"] = bytewise
        record["code_sha256"] = canonical
        record["fingerprint_method"] = "sha256-file-map-normalized-lf"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        changed += 1
    print(f"Canonical fingerprints: {changed} records; predictions/inputs/metrics unchanged")


if __name__ == "__main__":
    main()
