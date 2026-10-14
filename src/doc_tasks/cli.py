import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import uvicorn

from .api import create_app
from .benchmark import ROOT, benchmark_ocr, code_hash, run_comparison
from .runtime import Settings, analyze_pdf, readiness


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local Tev1 PDF obligation extraction")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8132)
    analyze = sub.add_parser("analyze")
    analyze.add_argument("pdf", type=Path)
    analyze.add_argument("--output", type=Path, required=True)
    sub.add_parser("health")
    ocr = sub.add_parser("benchmark-ocr")
    ocr.add_argument("--engine", choices=["paddle-v5", "paddle-vl", "tesseract"], required=True)
    ocr.add_argument("--split", choices=["dev", "test"], default="dev")
    compare = sub.add_parser("compare")
    compare.add_argument("--split", choices=["dev", "test"], default="dev")
    compare.add_argument("--mode", choices=["native", "ocr"], default="native")
    compare.add_argument("--engine", choices=["paddle-v5", "paddle-vl", "tesseract"], default="paddle-vl")
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--test-exposed", action="store_true",
                        help="Explicitly label a revised stack evaluated after inspecting final-test outcomes")
    args = parser.parse_args(argv)
    if args.command == "serve":
        uvicorn.run(create_app(), host="127.0.0.1", port=args.port, access_log=False)
    elif args.command == "analyze":
        result = analyze_pdf(args.pdf, lambda stage: print(stage, flush=True))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    elif args.command == "health":
        print(json.dumps(readiness(), indent=2))
    elif args.command == "benchmark-ocr":
        if args.split == "test":
            frozen = json.loads((ROOT / "evaluation/production-freeze.json").read_text(encoding="utf-8"))
            if frozen["code_sha256"] != code_hash():
                raise ValueError("Freeze required before held-out OCR")
        benchmark_ocr(args.engine, args.split)
    elif args.command == "compare":
        run_comparison(args.split, args.mode, args.engine)
    elif args.command == "freeze":
        settings = Settings()
        path = ROOT / "evaluation/production-freeze.json"
        if path.exists():
            raise ValueError("Existing freeze retained; do not silently overwrite a held-out protocol")
        path.write_text(json.dumps({"code_sha256": code_hash(), "model": settings.model,
                                   "fingerprint_method": "sha256-file-map-normalized-lf",
                                   "ocr": settings.ocr_engine,
                                   "frozen_at": datetime.now(UTC).isoformat(),
                                   "test_set_exposed": args.test_exposed,
                                   "decision_threshold": .5,
                                   "note": "Noul threshold is a decision rule, not calibrated correctness. Structural disagreements require review."},
                                  indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
