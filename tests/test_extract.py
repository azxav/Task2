from doc_tasks.decisions import DecisionAnswer
from doc_tasks.extract import extract, validate_grounding
from doc_tasks.schema import Document, FieldValue, Passage, SourceSpan


class ControlledDecisions:
    model = "test-controlled"
    calls = 0
    elapsed = 0

    def evaluate(self, state, questions):
        self.calls += 1
        answers = {}
        for q in questions:
            if q.type == "noul":
                if q.id == "obligation":
                    value = state.get("clause_ref") in ["1", "2", "3"]
                elif q.id == "default_applies":
                    value = state.get("clause_ref") == "2"
                else:
                    value = state.get("candidate", "") in ["Axborot texnologiyalari boshqarmasi",
                                                          "Huquqiy ekspertiza boshqarmasi"]
                answers[q.id] = DecisionAnswer(selected_id="yes" if value else "no",
                                                probabilities={"yes": float(value), "no": float(not value)})
            else:
                selected = "unknown"
                if q.id == "kind":
                    selected = "execution" if state.get("clause_ref") in ["1", "2"] else "none"
                elif q.id == "deadline":
                    selected = next((key for key, text in q.options.items() if text == "bir oy muddatda"),
                                    "unknown")
                answers[q.id] = DecisionAnswer(selected_id=selected,
                                                probabilities={key: float(key == selected) for key in q.options})
        return answers


def document():
    texts = [
        "1. Axborot texnologiyalari boshqarmasi hujjat loyihasini bir oy muddatda ishlab chiqsin va Kengashga kiritsin.",
        "2. Huquqiy ekspertiza boshqarmasi takliflar tayyorlasin.",
        "3. Muddati ko‘rsatilmagan topshiriqlar bir oy muddatda ijro etilsin.",
        "Ijrochi: N. Sobirova",
    ]
    return Document(spans=[SourceSpan(id=f"s{i}", page=1, text=text) for i, text in enumerate(texts)],
                    passages=[Passage(id=f"p{i}", kind="clause" if i < 3 else "footer",
                                      clause_ref=str(i+1) if i < 3 else None, span_ids=[f"s{i}"])
                              for i in range(4)])


def test_compound_and_inherited_deadline_keep_source_evidence():
    result = extract(document(), ControlledDecisions())
    assert len(result.tasks) == 3
    assert "ishlab chiqsin va Kengashga kiritsin" in result.tasks[0].instruction.text
    assert result.tasks[0].executors[0].text == "Axborot texnologiyalari boshqarmasi"
    assert result.tasks[1].executors[0].text == "Huquqiy ekspertiza boshqarmasi"
    assert result.tasks[1].deadline.text == "bir oy muddatda"
    assert set(result.tasks[1].deadline.source_ids) == {"s1", "s2"}
    assert all("Sobirova" not in (v.text or "") for t in result.tasks for v in t.executors)


def test_generated_field_text_is_rejected():
    import pytest
    with pytest.raises(ValueError, match="verbatim"):
        validate_grounding(FieldValue(text="invented executor", source_ids=["s1"]), document())


def test_negative_presence_decision_blocks_spurious_classification():
    class NoObligation(ControlledDecisions):
        def evaluate(self, state, questions):
            result = super().evaluate(state, questions)
            for q in questions:
                if q.id == "obligation":
                    result[q.id] = DecisionAnswer(selected_id="no", probabilities={"yes": .01, "no": .99})
            return result
    background = Document(spans=[SourceSpan(id="s", page=1, text="1. The project started last year.")],
                          passages=[Passage(id="p", kind="clause", clause_ref="1", span_ids=["s"])])
    assert extract(background, NoObligation()).tasks == []


def test_inherited_deadline_requires_separate_applicability_decision():
    class NoDefault(ControlledDecisions):
        def evaluate(self, state, questions):
            result = super().evaluate(state, questions)
            for q in questions:
                if q.id == "default_applies":
                    result[q.id] = DecisionAnswer(selected_id="no", probabilities={"yes": .01, "no": .99})
            return result
    result = extract(document(), NoDefault())
    assert result.tasks[1].deadline.status == "not_specified"
