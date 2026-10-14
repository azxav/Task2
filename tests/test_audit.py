from doc_tasks.decisions import DecisionAnswer, DecisionQuestion


def test_audit_records_rejected_choices_and_source_context():
    from doc_tasks.audit import AuditedDecisions
    class Model:
        model = "test"
        calls = 1
        elapsed = .1
        def evaluate(self, state, questions):
            return {"q": DecisionAnswer(selected_id="no", probabilities={"yes": .1, "no": .9})}
    client = AuditedDecisions(Model())
    question = DecisionQuestion(id="q", type="noul", instructions="An obligation?")
    client.evaluate({"passage": "Background only", "source_ids": ["p1"]}, [question])
    assert client.trace[0]["answers"]["q"]["selected_id"] == "no"
    assert client.trace[0]["state"]["source_ids"] == ["p1"]


def test_comparison_selection_and_input_hash_are_stable():
    from doc_tasks.benchmark import input_hash, select_documents
    manifest = {"documents": [{"id": "a", "split": "dev", "scanned": False},
                              {"id": "b", "split": "test", "scanned": True}]}
    assert [i["id"] for i in select_documents(manifest, "dev", "native")] == ["a"]
    assert input_hash({"x": 1, "y": 2}) == input_hash({"y": 2, "x": 1})
