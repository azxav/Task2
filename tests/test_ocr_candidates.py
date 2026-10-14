from doc_tasks.candidates import generate_candidates
from doc_tasks.schema import Document, Passage, SourceSpan


def test_merged_ocr_letterhead_keeps_name_without_contact_details():
    text = "RAQAMLI HUQUQIY XIZMATLAR AGENTLIGI 100011, Toshkent shahri. Tel.: 000"
    doc = Document(spans=[SourceSpan(id="s", page=1, text=text)],
                   passages=[Passage(id="p", kind="header", span_ids=["s"])])
    assert "RAQAMLI HUQUQIY XIZMATLAR AGENTLIGI" in {c.text for c in generate_candidates(doc)}


def test_ocr_damaged_month_remains_original_candidate():
    text = "4. Hududiy bo‘linmalar ishlarni 2026-yil 15-mardan boshlab tashkil etsin."
    doc = Document(spans=[SourceSpan(id="s", page=1, text=text)],
                   passages=[Passage(id="p", kind="clause", clause_ref="4", span_ids=["s"])])
    assert "2026-yil 15-mardan boshlab" in {c.text for c in generate_candidates(doc) if c.role_hint == "deadline"}


def test_vl_underline_markup_is_transcribed_without_inventing_number():
    from doc_tasks.ocr_layout import parse_vl_page
    page = parse_vl_page({"width": 600, "height": 800, "parsing_res_list": [
        {"block_label": "text", "block_bbox": [40, 50, 300, 80],
         "block_content": r"$ \underline{\text{08.09.2026}} $ N№ $ \underline{\text{03-12/1456}} $"}]}, 1)
    assert page.spans[0].text == "08.09.2026 N№ 03-12/1456"
    assert "underline" in page.raw_result["parsing_res_list"][0]["block_content"]
