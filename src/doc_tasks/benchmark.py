"""Reproducible local comparisons; hold-out access requires a frozen stack."""
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import httpx
import psutil
from rapidfuzz.distance import Levenshtein

from .audit import AuditedDecisions
from .candidates import generate_candidates
from .decisions import OllamaDecisions, QwenDecisions
from .evaluate import evaluate, normalize
from .extract import extract
from .ocr import NoOCR, ProcessOCR
from .pdf import read_pdf
from .schema import Document

ROOT = Path(__file__).resolve().parents[2]
MODELS = ["tev1:0.8b-q8_0", "tev1:4b-q4_K_M", "qwen3.5:4b"]


def input_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def code_hash(*, normalize_line_endings=True):
    names = ["schema", "candidates", "decisions", "extract", "ocr", "ocr_layout", "roles", "pdf", "structure", "network", "audit", "language", "segmentation"]
    files = [ROOT / "src/doc_tasks" / (name + ".py") for name in names] + list((ROOT / "ocr-runtime").glob("*.py"))
    files += [ROOT / "model-profiles.json", ROOT / "ocr-runtime/models-lock.json"]
    def digest(path):
        value = path.read_bytes()
        if normalize_line_endings:
            value = value.replace(b"\r\n", b"\n")
        return hashlib.sha256(value).hexdigest()
    return input_hash({str(p.relative_to(ROOT)): digest(p) for p in files})


def select_documents(manifest, split, mode):
    return [item for item in manifest["documents"] if item["split"] == split
            and item["scanned"] == (mode == "ocr")]


class ResourceMonitor:
    def __init__(self, inference=False, gpu=False):
        self.inference = inference
        self.gpu = gpu or inference

    def __enter__(self):
        self.peak_rss = 0
        self.peak_gpu_mib = 0
        self.stop = threading.Event()
        def monitor():
            root = psutil.Process()
            while not self.stop.is_set():
                rss = 0
                processes = [root, *root.children(recursive=True)]
                if self.inference:
                    pidfile = ROOT / ".cache/runtime/ollama.pid"
                    try:
                        server = psutil.Process(int(pidfile.read_text().strip()))
                        if server.name().lower() == "ollama.exe":
                            processes.extend([server, *server.children(recursive=True)])
                    except (OSError, ValueError, psutil.Error):
                        pass
                for process in processes:
                    try:
                        rss += process.memory_info().rss
                    except psutil.Error:
                        pass
                self.peak_rss = max(self.peak_rss, rss)
                if self.gpu:
                    try:
                        gpu = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                             capture_output=True, timeout=3, check=True)
                        self.peak_gpu_mib = max(self.peak_gpu_mib, int(gpu.stdout.decode().strip().splitlines()[0]))
                    except (OSError, ValueError, subprocess.SubprocessError):
                        pass
                self.stop.wait(1 if self.gpu else .25)
        self.thread = threading.Thread(target=monitor, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join()


def local_ocr(engine):
    os.environ["OCR_MODEL_ROOT"] = str(ROOT / ".cache/paddlex/official_models")
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    os.environ["TESSERACT_BIN"] = str(ROOT / ".runtime/tesseract/Library/bin/tesseract.exe")
    os.environ["TESSDATA_DIR"] = str(ROOT / ".cache/tessdata")
    env = ".venv-vl" if engine == "paddle-vl" else ".venv-ocr"
    return ProcessOCR(engine, [str(ROOT / env / "Scripts/python.exe"), "-X", "utf8",
                               str(ROOT / "ocr-runtime/worker.py"), "--engine", engine], timeout=600)


def benchmark_ocr(engine, split="dev"):
    root = ROOT / "evaluation"
    if split == "test":
        path = root / "production-freeze.json"
        if not path.exists():
            raise ValueError("Freeze required before held-out OCR")
        frozen = json.loads(path.read_text(encoding="utf-8"))
        if frozen["code_sha256"] != code_hash():
            raise ValueError("Freeze changed; held-out OCR refused")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    output = root / "results" / f"{split}-ocr-{engine}"
    output.mkdir(parents=True, exist_ok=True)
    for item in select_documents(manifest, split, "ocr"):
        path = output / (item["id"] + ".json")
        started = time.perf_counter()
        with ResourceMonitor(gpu=engine == "paddle-vl") as resources:
            document = read_pdf(root / item["path"], local_ocr(engine))
        reference_item = next(i for i in manifest["documents"] if i["family"] == item["family"] and not i["scanned"])
        reference = read_pdf(root / reference_item["path"], NoOCR())
        expected = normalize(" ".join(s.text for s in reference.spans))
        actual = normalize(" ".join(s.text for s in document.spans))
        gold = json.loads((root / item["gold"]).read_text(encoding="utf-8"))
        critical = [v["text"] for v in gold["metadata"].values()] + [v for t in gold["tasks"]
                    for v in [*t["executors"], t["deadline"]] if v]
        record = {"engine": engine, "split": split, "document": document.model_dump(),
                  "input_sha256": input_hash(document.model_dump()), "code_sha256": code_hash(),
                  "seconds": time.perf_counter()-started, "peak_process_tree_rss_bytes": resources.peak_rss,
                  "peak_gpu_memory_mib": resources.peak_gpu_mib,
                  "layout_sensitive_cer": Levenshtein.distance(expected, actual) / max(1, len(expected)),
                  "critical_exact_present": sum(normalize(v) in actual for v in critical),
                  "critical_total": len(critical), "table_rows": sum(p.kind == "table_row" for p in document.passages),
                  "note": "CER includes reading-order differences. Critical exact coverage normalizes case/apostrophes/whitespace."}
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(engine, item["id"], round(record["seconds"], 1), record["critical_exact_present"],
              "/", len(critical), "rows", record["table_rows"], flush=True)
    return output


def run_comparison(split="dev", mode="native", engine="paddle-vl", models=MODELS, base_url="http://127.0.0.1:11435"):
    root = ROOT / "evaluation"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if split == "test":
        freeze = json.loads((root / "production-freeze.json").read_text(encoding="utf-8"))
        if freeze["code_sha256"] != code_hash():
            raise ValueError("Stack changed since freeze; held-out evaluation refused")
    items = select_documents(manifest, split, mode)
    inputs = {}
    for item in items:
        if mode == "ocr":
            record = json.loads((root / "results" / f"{split}-ocr-{engine}" / (item["id"] + ".json")).read_text(encoding="utf-8"))
            inputs[item["id"]] = Document.model_validate(record["document"])
        else:
            inputs[item["id"]] = read_pdf(root / item["path"], NoOCR())
    output = root / "results" / f"{split}-{mode}-final"
    output.mkdir(parents=True, exist_ok=True)
    stack_hash = code_hash()
    with httpx.Client(base_url=base_url, trust_env=False, timeout=10) as http:
        runtime = {"version": http.get("/api/version").raise_for_status().json(),
                   "models": http.get("/api/tags").raise_for_status().json(),
                   "profiles": {model: http.post("/api/show", json={"model": model}).raise_for_status().json()
                                for model in models}}
    (output / "runtime.json").write_text(json.dumps(runtime, ensure_ascii=False, indent=2), encoding="utf-8")
    for model in models:
        factory = QwenDecisions if model.startswith("qwen") else OllamaDecisions
        with httpx.Client(base_url=base_url, trust_env=False, timeout=30) as http:
            for loaded in http.get("/api/ps").raise_for_status().json().get("models", []):
                http.post("/api/generate", json={"model": loaded["name"], "keep_alive": 0}).raise_for_status()
        for index, item in enumerate(items):
            document = inputs[item["id"]]
            gold = json.loads((root / item["gold"]).read_text(encoding="utf-8"))
            client = AuditedDecisions(factory(model, base_url))
            try:
                started = time.perf_counter()
                with ResourceMonitor(inference=True) as resources:
                    result = extract(document, client)
                candidates = generate_candidates(document)
                expected = [v["text"] for v in gold["metadata"].values()] + [v for t in gold["tasks"]
                            for v in [*t["executors"], t["deadline"]] if v]
                available = {normalize(c.text) for c in candidates}
                record = {"model": model, "split": split, "document": item["id"],
                          "input_sha256": input_hash(document.model_dump()), "code_sha256": stack_hash,
                          "analysis": result.model_dump(), "metrics": evaluate(gold, result.model_dump()),
                          "seconds": time.perf_counter()-started,
                          "load_state": "cold" if index == 0 else "warm",
                          "peak_process_tree_rss_bytes": resources.peak_rss,
                          "peak_gpu_memory_mib": resources.peak_gpu_mib,
                          "resource_note": "One-second samples. RSS includes owned Ollama server/runner. GPU reading is whole-device memory, includes desktop baseline.",
                          "candidate_coverage": {"present": sum(normalize(v) in available for v in expected), "total": len(expected)},
                          "decisions": client.trace}
                path = output / (model.replace(":", "-") + "--" + item["id"] + ".json")
                path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
                print(model, item["id"], {k: record["metrics"][k] for k in ["matched_tasks", "missed_tasks",
                      "spurious_tasks", "executor_errors", "deadline_errors", "metadata_correct"]}, flush=True)
            finally:
                client.close()
    return output
