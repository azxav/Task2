import shutil

import pytest

from doc_tasks import benchmark


def test_stack_hash_covers_pinned_model_configuration(tmp_path, monkeypatch):
    root = benchmark.ROOT
    (tmp_path / "src/doc_tasks").mkdir(parents=True)
    (tmp_path / "ocr-runtime").mkdir()
    for path in (root / "src/doc_tasks").glob("*.py"):
        shutil.copy2(path, tmp_path / "src/doc_tasks" / path.name)
    for path in (root / "ocr-runtime").glob("*.py"):
        shutil.copy2(path, tmp_path / "ocr-runtime" / path.name)
    for name in ("model-profiles.json", "ocr-runtime/models-lock.json"):
        shutil.copy2(root / name, tmp_path / name)
    monkeypatch.setattr(benchmark, "ROOT", tmp_path)
    before = benchmark.code_hash()
    data = (tmp_path / "model-profiles.json").read_bytes().replace(b"\r\n", b"\n")
    (tmp_path / "model-profiles.json").write_bytes(data)
    assert benchmark.code_hash() == before
    (tmp_path / "model-profiles.json").write_text('{"changed":true}')
    assert benchmark.code_hash() != before


def test_direct_heldout_ocr_requires_freeze(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="Freeze"):
        benchmark.benchmark_ocr("paddle-vl", split="test")


def test_revised_protocol_explicitly_labels_exposed_test(tmp_path, monkeypatch):
    import json

    from doc_tasks import cli
    (tmp_path / "evaluation").mkdir()
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "code_hash", lambda: "revised-stack")
    cli.main(["freeze", "--test-exposed"])
    assert json.loads((tmp_path / "evaluation/production-freeze.json").read_text())["test_set_exposed"] is True
