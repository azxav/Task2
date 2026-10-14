from pathlib import Path

import pytest
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from doc_tasks.ocr import OCRPage
from doc_tasks.pdf import InvalidPDF, read_pdf
from doc_tasks.schema import SourceSpan


def make_pdf(path: Path, mixed=False):
    writer = canvas.Canvas(str(path), pagesize=(600, 800))
    writer.drawString(40, 750, "LOCAL AGENCY")
    writer.drawString(40, 700, "1. IT Department must develop the draft and submit it.")
    writer.drawString(40, 683, "Deadline: within one month.")
    if mixed:
        writer.showPage()
        image = Image.new("RGB", (600, 800), "white")
        writer.drawImage(ImageReader(image), 0, 0, width=600, height=800)
    writer.save()


class FakeOCR:
    name = "test-ocr"

    def __init__(self):
        self.calls = []

    def recognize(self, image_path, page):
        self.calls.append(page)
        return OCRPage(
            page=page, width=600, height=800,
            spans=[SourceSpan(id=f"p{page}-line1", page=page, text="2. Legal Department must approve.",
                              bbox=(40, 60, 400, 78))],
        )


def test_mixed_pdf_uses_ocr_only_for_image_page(tmp_path):
    path = tmp_path / "mixed.pdf"
    make_pdf(path, mixed=True)
    ocr = FakeOCR()
    document = read_pdf(path, ocr)
    assert ocr.calls == [2]
    assert {span.page for span in document.spans} == {1, 2}
    instruction = next(p for p in document.passages if p.clause_ref == "1")
    text = " ".join(s.text for s in document.spans if s.id in instruction.span_ids)
    assert "develop the draft and submit it" in text
    assert "within one month" in text


def test_invalid_pdf_is_rejected(tmp_path):
    path = tmp_path / "bad.pdf"
    path.write_bytes(b"not a pdf")
    with pytest.raises(InvalidPDF):
        read_pdf(path, FakeOCR())


def test_real_native_tables_keep_correct_cells():
    root = Path(__file__).parents[1]
    path = root / "evaluation/source/Files Task_2/matnli/NAMUNA_2_jadval.pdf"
    document = read_pdf(path, FakeOCR())
    rows = [p for p in document.passages if p.kind == "table_row"]
    assert len(rows) == 5
    by_id = {s.id: s.text for s in document.spans}
    assert "1-may" in " ".join(by_id[s] for s in rows[0].table_cells["deadline"])
    assert "15-iyun" in " ".join(by_id[s] for s in rows[1].table_cells["deadline"])
