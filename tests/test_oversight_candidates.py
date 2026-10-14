from doc_tasks.candidates import generate_candidates
from doc_tasks.schema import Document, Passage, SourceSpan


def test_named_oversight_unit_is_not_swallowed_by_clause_prefix():
    doc = Document(spans=[SourceSpan(id="s1", page=1, text=
        "7. Mazkur qaror ijrosini nazorat qilish Agentlik direktorining birinchi o‘rinbosari zimmasiga yuklansin.")],
        passages=[Passage(id="p1", kind="clause", span_ids=["s1"], clause_ref="7")])
    assert "Agentlik direktorining birinchi o‘rinbosari" in {c.text for c in generate_candidates(doc)}
    assert not any(c.text.startswith("Mazkur") for c in generate_candidates(doc) if c.role_hint == "executor")
