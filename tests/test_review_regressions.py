from test_extract import ControlledDecisions

from doc_tasks.extract import extract
from doc_tasks.ocr import OCRPage
from doc_tasks.schema import Document, Passage, SourceSpan
from doc_tasks.structure import build_passages


def test_continuation_page_top_obligation_is_not_header():
    page = OCRPage(page=2, width=600, height=800, spans=[SourceSpan(
        id="s", page=2, text="Texnik bo‘lim hisobotni tayyorlasin.", bbox=(40, 40, 550, 60))])
    result = extract(build_passages([page]), ControlledDecisions())
    assert len(result.tasks) == 1


def test_wrapped_first_page_obligation_keeps_subject_prefix():
    page = OCRPage(page=1, width=600, height=800, spans=[
        SourceSpan(id="a", page=1, text="Texnik bo‘lim hujjat loyihasini", bbox=(40, 80, 550, 96)),
        SourceSpan(id="b", page=1, text="bir oy muddatda tayyorlasin.", bbox=(40, 100, 550, 116)),
    ])
    result = extract(build_passages([page]), ControlledDecisions())
    assert result.tasks[0].instruction.text == "Texnik bo‘lim hujjat loyihasini bir oy muddatda tayyorlasin."
    assert result.tasks[0].executors[0].text == "Texnik bo‘lim"


def test_final_page_signer_is_selectable():
    from doc_tasks.decisions import DecisionAnswer

    class Signer(ControlledDecisions):
        def evaluate(self, state, questions):
            result = super().evaluate(state, questions)
            for q in questions:
                if q.id == "signer":
                    selected = next((k for k, v in q.options.items() if v == "O. Saidov"), "unknown")
                    result[q.id] = DecisionAnswer(selected_id=selected, probabilities={selected: 1})
            return result

    document = Document(spans=[SourceSpan(id="s", page=2, text="Direktor O. Saidov")],
                        passages=[Passage(id="p", kind="paragraph", span_ids=["s"])])
    assert extract(document, Signer()).metadata.signer.text == "O. Saidov"


def test_separate_executors_and_deadlines_split_but_keep_source():
    from doc_tasks.decisions import DecisionAnswer

    class LocalDeadline(ControlledDecisions):
        def evaluate(self, state, questions):
            result = super().evaluate(state, questions)
            for q in questions:
                if q.id == "deadline":
                    selected = next((k for k, v in q.options.items() if "muddatda" in v), "unknown")
                    result[q.id] = DecisionAnswer(selected_id=selected, probabilities={selected: 1})
            return result

    text = "1. Texnik bo‘lim loyihani bir oy muddatda tayyorlasin; Huquqiy bo‘lim hisobotni ikki oy muddatda taqdim etsin."
    document = Document(spans=[SourceSpan(id="s", page=1, text=text)],
                        passages=[Passage(id="p", kind="clause", clause_ref="1", span_ids=["s"])])
    result = extract(document, LocalDeadline())
    assert len(result.tasks) == 2
    assert [t.deadline.text for t in result.tasks] == ["bir oy muddatda", "ikki oy muddatda"]
    assert [[v.text for v in t.executors] for t in result.tasks] == [["Texnik bo‘lim"], ["Huquqiy bo‘lim"]]
    assert all(s.parent_id == "s" for s in result.sources if s.id != "s")


def test_develop_submit_same_draft_survives_wrong_boundary_decision():
    from doc_tasks.decisions import DecisionAnswer

    class SplitAll(ControlledDecisions):
        def evaluate(self, state, questions):
            result = super().evaluate(state, questions)
            for q in questions:
                if q.id == "task_boundary":
                    result[q.id] = DecisionAnswer(selected_id="split", probabilities={"split": 1, "preserve": 0})
            return result

    text = "1. Texnik bo‘lim loyihani bir oy muddatda ishlab chiqsin va Kengashga kiritsin."
    document = Document(spans=[SourceSpan(id="s", page=1, text=text)],
                        passages=[Passage(id="p", kind="clause", clause_ref="1", span_ids=["s"])])
    assert len(extract(document, SplitAll()).tasks) == 1


def test_coordination_unit_does_not_split_same_draft():
    text = "1. Texnik bo‘lim hujjat loyihasini ishlab chiqsin va Huquqiy bo‘lim bilan kelishgan holda Kengashga kiritsin."
    document = Document(spans=[SourceSpan(id="s", page=1, text=text)],
                        passages=[Passage(id="p", kind="clause", clause_ref="1", span_ids=["s"])])
    assert len(extract(document, ControlledDecisions()).tasks) == 1
