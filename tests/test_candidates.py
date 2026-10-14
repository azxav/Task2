from doc_tasks.candidates import generate_candidates
from doc_tasks.schema import Document, Passage, SourceSpan


def test_multiple_executors_and_deadline_candidates():
    text = ("1. Axborot xavfsizligi bo‘limi Sun’iy intellekt laboratoriyasi bilan birgalikda "
            "takliflarni o‘n kun muddatda kiritsin.")
    document = Document(spans=[SourceSpan(id="s1", page=1, text=text)],
                        passages=[Passage(id="p1", kind="clause", span_ids=["s1"], clause_ref="1")])
    candidates = generate_candidates(document)
    values = {candidate.text for candidate in candidates}
    assert "Axborot xavfsizligi bo‘limi" in values
    assert "Sun’iy intellekt laboratoriyasi" in values
    assert "o‘n kun muddatda" in values
    assert all(candidate.source_ids == ["s1"] for candidate in candidates)


def test_candidate_role_does_not_confuse_footer_preparer():
    document = Document(spans=[SourceSpan(id="s1", page=1, text="Ijrochi: N. Sobirova")],
                        passages=[Passage(id="p1", kind="footer", span_ids=["s1"])])
    people = [c for c in generate_candidates(document) if c.text == "N. Sobirova"]
    assert people and people[0].role_hint == "preparer"


def test_plural_regional_units_are_candidates():
    doc = Document(spans=[SourceSpan(id="s1", page=1, text="4. Hududiy bo‘linmalar ishlarni tashkil etsin.")],
                   passages=[Passage(id="p1", kind="clause", span_ids=["s1"])])
    assert "Hududiy bo‘linmalar" in {c.text for c in generate_candidates(doc)}


def test_recurring_deadline_does_not_stop_inside_yakunidan():
    text = "Axborot kiritsin har chorak yakunidan keyingi oyning 10-sanasiga qadar."
    doc = Document(spans=[SourceSpan(id="s1", page=1, text=text)],
                   passages=[Passage(id="p1", kind="paragraph", span_ids=["s1"])])
    assert "har chorak yakunidan keyingi oyning 10-sanasiga qadar" in {c.text for c in generate_candidates(doc)}


def test_working_day_expression_is_preserved():
    doc = Document(spans=[SourceSpan(id="s1", page=1, text="Ma’lumotni uch ish kuni ichida taqdim eting.")],
                   passages=[Passage(id="p1", kind="paragraph", span_ids=["s1"])])
    assert "uch ish kuni ichida" in {c.text for c in generate_candidates(doc)}


def test_header_column_continuation_excludes_left_reply_placeholder():
    spans = [SourceSpan(id="r1", page=1, text="Adliya organlari va muassasalarida axborot", bbox=(300, 100, 550, 112)),
             SourceSpan(id="l1", page=1, text="____-son xatga", bbox=(40, 114, 200, 126)),
             SourceSpan(id="r2", page=1, text="texnologiyalarini rivojlantirish markaziga", bbox=(300, 117, 550, 129))]
    doc = Document(spans=spans, passages=[Passage(id=f"p{i}", kind="header", span_ids=[s.id])
                                         for i, s in enumerate(spans)])
    candidates = generate_candidates(doc)
    candidate = next(c for c in candidates if c.text ==
        "Adliya organlari va muassasalarida axborot texnologiyalarini rivojlantirish markaziga")
    assert candidate.source_ids == ["r1", "r2"]


def test_multiline_sender_candidate_excludes_contact_line():
    spans = [SourceSpan(id="s1", page=1, text="MA’LUMOTLAR XAVFSIZLIGI VA INTEGRATSIYA"),
             SourceSpan(id="s2", page=1, text="AGENTLIGI"),
             SourceSpan(id="s3", page=1, text="100060, Toshkent shahri. Tel.: +998")]
    doc = Document(spans=spans, passages=[Passage(id="p1", kind="header", span_ids=[s.id for s in spans])])
    candidate = next(c for c in generate_candidates(doc) if c.text ==
        "MA’LUMOTLAR XAVFSIZLIGI VA INTEGRATSIYA AGENTLIGI")
    assert candidate.source_ids == ["s1", "s2"]
