from doc_tasks.ocr import OCRPage, TableRow
from doc_tasks.schema import SourceSpan
from doc_tasks.structure import build_passages


def test_table_cells_keep_row_and_column():
    spans = [SourceSpan(id=f"s{i}", page=1, text=t) for i, t in enumerate(
        ["Develop module", "IT", "1 June", "Train staff", "HR", "2 July"]
    )]
    page = OCRPage(page=1, width=600, height=800, spans=spans, rows=[
        TableRow(id="r1", reference="1", cells={"instruction": ["s0"], "executor": ["s1"], "deadline": ["s2"]}),
        TableRow(id="r2", reference="2", cells={"instruction": ["s3"], "executor": ["s4"], "deadline": ["s5"]}),
    ])
    document = build_passages([page])
    assert document.passages[0].table_cells["deadline"] == ["s2"]
    assert document.passages[1].table_cells["deadline"] == ["s5"]


def test_missing_ocr_cell_is_diagnostic():
    page = OCRPage(page=1, width=600, height=800,
                   spans=[SourceSpan(id="s1", page=1, text="Develop module")],
                   rows=[TableRow(id="r1", reference="1", cells={"instruction": ["s1"], "executor": [], "deadline": []})])
    document = build_passages([page])
    assert any("executor" in warning for warning in document.warnings)
