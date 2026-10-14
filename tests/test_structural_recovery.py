from doc_tasks.decisions import DecisionAnswer
from doc_tasks.extract import extract
from doc_tasks.schema import Document, Passage, SourceSpan


class DisagreeingModel:
    model = "controlled-negative-links"
    calls = 0
    elapsed = 0
    def evaluate(self, state, questions):
        return {q.id: DecisionAnswer(selected_id="no" if q.type == "noul" else
                                     "execution" if q.id == "kind" else "unknown",
                                     probabilities={"yes": .1, "no": .9} if q.type == "noul" else
                                     {k: float(k in ("unknown", "execution")) for k in q.options})
                for q in questions}


def test_clear_imperative_and_subject_are_retained_with_review():
    text = "2. Texnik bo‘lim loyihani ishlab chiqsin va Kengashga kiritsin."
    doc = Document(spans=[SourceSpan(id="s", page=1, text=text)],
                   passages=[Passage(id="p", kind="clause", clause_ref="2", span_ids=["s"])])
    result = extract(doc, DisagreeingModel())
    assert len(result.tasks) == 1
    assert result.tasks[0].instruction.text == text
    assert [v.text for v in result.tasks[0].executors] == ["Texnik bo‘lim"]
    assert result.tasks[0].review_reasons


def test_second_person_resolves_one_multiline_addressee_despite_fragment():
    doc = Document(spans=[SourceSpan(id="h1", page=1, text="Adliya organlarida axborot", bbox=(300, 50, 550, 65)),
                          SourceSpan(id="h2", page=1, text="texnologiyalarini rivojlantirish markaziga", bbox=(300, 70, 550, 85)),
                          SourceSpan(id="s", page=1, text="Hisobotni taqdim etishingiz so‘raladi.", bbox=(40, 400, 550, 420))],
                   passages=[Passage(id="h1", kind="header", span_ids=["h1"]),
                             Passage(id="h2", kind="header", span_ids=["h2"]),
                             Passage(id="p", kind="paragraph", span_ids=["s"])])
    result = extract(doc, DisagreeingModel())
    assert [v.text for v in result.tasks[0].executors] == ["Adliya organlarida axborot texnologiyalarini rivojlantirish markaziga"]
    assert set(result.tasks[0].executors[0].source_ids) == {"h1", "h2", "s"}


def test_named_responsible_person_is_not_lost_to_unit_only_patterns():
    doc = Document(spans=[SourceSpan(id="s", page=1, text="1. O. Saidov texnik hisobotni tayyorlasin.")],
                   passages=[Passage(id="p", kind="clause", clause_ref="1", span_ids=["s"])])
    assert [v.text for v in extract(doc, DisagreeingModel()).tasks[0].executors] == ["O. Saidov"]
