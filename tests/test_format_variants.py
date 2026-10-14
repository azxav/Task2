from doc_tasks.candidates import generate_candidates
from doc_tasks.extract import _layout_only, _metadata
from doc_tasks.ocr_layout import parse_vl_page
from doc_tasks.schema import Document, Metadata, Passage, SourceSpan


def document(text, kind="header"):
    return Document(spans=[SourceSpan(id="s", page=1, text=text)],
                    passages=[Passage(id="p", kind=kind, span_ids=["s"])])


def test_ambiguous_deadline_apostrophe_variants_keep_original():
    for apostrophe in ("'", "‘", "’", "ʻ", "ʼ"):
        text = f"Mas’ul ijrochilar tomonidan o{apostrophe}z vaqtida ijro etilishi ta’minlansin."
        candidates = generate_candidates(document(text, "paragraph"))
        assert f"o{apostrophe}z vaqtida" in {c.text for c in candidates if c.role_hint == "deadline"}


def test_number_candidate_survives_damaged_marker_without_repair():
    text = "12.10.2026 N $ _{x} $ 09-02/3178"
    assert "09-02/3178" in {c.text for c in generate_candidates(document(text)) if c.role_hint == "number"}


def test_merged_sender_title_has_selectable_organization_prefix():
    from doc_tasks.decisions import DecisionAnswer

    class SelectPrefix:
        def evaluate(self, state, questions):
            return {q.id: DecisionAnswer(selected_id=next(
                (k for k, v in q.options.items() if v == "HUQUQIY XIZMATLAR KENGASHINING"), "unknown"),
                probabilities={"unknown": 1}) for q in questions}

    doc = document("HUQUQIY XIZMATLAR KENGASHINING QARORX")
    assert _metadata(doc, generate_candidates(doc), SelectPrefix()).sender.text == "HUQUQIY XIZMATLAR KENGASHINING"


def test_sender_prefix_fix_does_not_restore_suffix_fragments():
    from doc_tasks.decisions import DecisionAnswer

    class PreferBadSuffix:
        def evaluate(self, state, questions):
            return {q.id: DecisionAnswer(selected_id=next(
                (k for k, v in q.options.items() if v == "KENGASHINING"), next(
                    (k for k, v in q.options.items() if v == "HUQUQIY XIZMATLAR KENGASHINING"), "unknown")),
                probabilities={"unknown": 1}) for q in questions}

    doc = Document(spans=[SourceSpan(id="a", page=1, text="HUQUQIY XIZMATLAR"),
                          SourceSpan(id="b", page=1, text="KENGASHINING")],
                   passages=[Passage(id="p", kind="header", span_ids=["a", "b"])])
    assert _metadata(doc, generate_candidates(doc), PreferBadSuffix()).sender.text == "HUQUQIY XIZMATLAR KENGASHINING"


def test_vl_table_escape_linebreak_is_formatting_not_a_new_word():
    raw = {"width": 600, "height": 800, "parsing_res_list": [{
        "block_label": "table", "block_bbox": [20, 50, 580, 500], "block_content":
        "<table><tr><td>№</td><td>Topshiriq</td><td>Ijrochi</td><td>Muddat</td></tr>"
        "<tr><td>1</td><td>Modulni joriy etish</td><td>Texnik\\nbo‘lim</td><td>bir oy ichida</td></tr></table>"}]}
    page = parse_vl_page(raw, 1)
    assert "Texnik bo‘lim" in {s.text for s in page.spans}
    assert "\\n" in page.raw_result["parsing_res_list"][0]["block_content"]


def test_referenced_agreement_date_does_not_make_duplicate_intro_a_task():
    text = "2026-yil 4-oktabrda imzolangan kelishuv doirasida quyidagi jadvaldagi topshiriqlarni bajarishingizni so‘raymiz."
    doc = document(text, "paragraph")
    doc.spans.append(SourceSpan(id="t", page=1, text="Modulni joriy etish"))
    doc.passages.append(Passage(id="table", kind="table_row", span_ids=["t"], table_cells={"instruction": ["t"]}))
    assert _layout_only(doc, doc.passages[0], Metadata(), 0)
