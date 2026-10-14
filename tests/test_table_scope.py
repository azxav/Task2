from doc_tasks.candidates import generate_candidates
from doc_tasks.extract import scoped_candidates
from doc_tasks.schema import Document, Passage, SourceSpan


def test_table_field_candidates_stay_in_their_cell():
    spans = [SourceSpan(id="task", page=1, text="Elektron modulini ishga tushirish"),
             SourceSpan(id="exec", page=1, text="Axborot texnologiyalari boshqarmasi"),
             SourceSpan(id="deadline", page=1, text="tizim tayyor bo‘lgandan so‘ng 2 oy ichida")]
    row = Passage(id="row", kind="table_row", span_ids=[s.id for s in spans],
                  table_cells={"instruction": ["task"], "executor": ["exec"], "deadline": ["deadline"]})
    doc = Document(spans=spans, passages=[row])
    candidates = generate_candidates(doc)
    executors = scoped_candidates(doc, row, candidates, "executor")
    deadlines = scoped_candidates(doc, row, candidates, "deadline")
    assert {c.text for c in executors} == {"Axborot texnologiyalari boshqarmasi"}
    assert {c.text for c in deadlines} == {"tizim tayyor bo‘lgandan so‘ng 2 oy ichida"}


def test_declared_task_table_row_survives_model_disagreement():
    from doc_tasks.decisions import DecisionAnswer
    from doc_tasks.extract import extract
    class NegativeModel:
        model = "negative-test"
        calls = 0
        elapsed = 0
        def evaluate(self, state, questions):
            return {q.id: DecisionAnswer(selected_id="no" if q.type == "noul" else
                                         "none" if q.id == "kind" else "unknown",
                                         probabilities={"yes": .1, "no": .9} if q.type == "noul" else
                                         {key: float(key in ["none", "unknown"]) for key in q.options})
                    for q in questions}
    doc = Document(spans=[SourceSpan(id="s1", page=1, text="Prepare technical requirements")],
                   passages=[Passage(id="row1", kind="table_row", span_ids=["s1"],
                                      table_cells={"instruction": ["s1"], "executor": [], "deadline": []})])
    result = extract(doc, NegativeModel())
    assert len(result.tasks) == 1
    assert result.tasks[0].instruction.text == "Prepare technical requirements"
    assert result.tasks[0].review_reasons
