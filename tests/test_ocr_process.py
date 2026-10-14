import json
import sys

import pytest

from doc_tasks.ocr import OCRUnavailable, ProcessOCR


def test_local_worker_output_is_validated(tmp_path):
    worker = tmp_path / "worker.py"
    worker.write_text("import sys,json,pathlib\n"
                      "out=sys.argv[sys.argv.index('--output')+1]\n"
                      "page=int(sys.argv[sys.argv.index('--page')+1])\n"
                      "pathlib.Path(out).write_text(json.dumps({'page':page,'width':600,'height':800,"
                      "'spans':[{'id':'s1','page':page,'text':'Read source'}]}))\n")
    page = ProcessOCR("fake", [sys.executable, str(worker)]).recognize(tmp_path / "input.png", 2)
    assert page.page == 2
    assert page.spans[0].text == "Read source"


def test_worker_failure_does_not_use_stale_output(tmp_path):
    image = tmp_path / "input.png"
    image.with_suffix(".ocr.json").write_text(json.dumps({"page":1,"width":1,"height":1,"spans":[]}))
    worker = tmp_path / "fail.py"
    worker.write_text("raise SystemExit(1)")
    with pytest.raises(OCRUnavailable):
        ProcessOCR("fake", [sys.executable, str(worker)]).recognize(image, 1)
