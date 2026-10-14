from doc_tasks.candidates import Candidate, generate_candidates
from doc_tasks.decisions import DecisionAnswer
from doc_tasks.extract import _choose, extract
from doc_tasks.schema import Document, Passage, SourceSpan


class Selector:
    model = "test"
    calls = 0
    elapsed = 0

    def evaluate(self, state, questions):
        answers = {}
        for q in questions:
            if q.type == "noul":
                answers[q.id] = DecisionAnswer(selected_id="no", probabilities={"yes": .1, "no": .9})
            else:
                key = next((key for key, value in q.options.items() if value == "target"), "unknown")
                if q.id == "kind":
                    key = "execution"
                answers[q.id] = DecisionAnswer(selected_id=key, probabilities={k: float(k == key) for k in q.options})
        return answers


def test_choices_beyond_first_batch_are_considered():
    candidates = [Candidate(id=f"c{i}", text="target" if i == 28 else f"item {i}",
                            source_ids=["s"], passage_id="p", role_hint="executor") for i in range(30)]
    assert _choose(Selector(), {}, "executor", "Choose target", candidates).text == "target"


def test_number_prefix_does_not_match_words_starting_with_no():
    doc = Document(spans=[SourceSpan(id="s", page=1, text="Noyabr oyida tashkilot nomlari")],
                   passages=[Passage(id="p", kind="paragraph", span_ids=["s"])])
    assert not [c for c in generate_candidates(doc) if c.role_hint == "number"]


def test_explicit_executor_cell_survives_semantic_disagreement():
    doc = Document(spans=[SourceSpan(id="t", page=1, text="Modulni joriy etish"),
                          SourceSpan(id="e", page=1, text="Texnik bo‘lim, Ishchi guruh")],
                   passages=[Passage(id="p", kind="table_row", span_ids=["t", "e"],
                                     table_cells={"instruction": ["t"], "executor": ["e"]})])
    result = extract(doc, Selector())
    assert [v.text for v in result.tasks[0].executors] == ["Texnik bo‘lim", "Ishchi guruh"]
    assert result.tasks[0].review_reasons


def test_vl_html_retains_cells_and_reports_unknown_geometry():
    from doc_tasks.ocr_layout import parse_vl_page
    result = parse_vl_page({"width": 200, "height": 300, "parsing_res_list": [
        {"block_label": "table", "block_bbox": [10, 40, 190, 200], "block_content":
         "<table><tr><td>№</td><td>Topshiriq mazmuni</td><td>Mas’ul ijrochi</td><td>Muddat</td></tr>"
         "<tr><td>1</td><td>Draft &amp; submit</td><td>A, B</td><td>uch ish kuni ichida</td></tr></table>"}
    ]}, 2)
    assert result.rows[0].cells.keys() >= {"instruction", "executor", "deadline"}
    lookup = {s.id: s for s in result.spans}
    assert lookup[result.rows[0].cells["instruction"][0]].text == "Draft & submit"
    assert result.diagnostics


def test_progress_report_topic_is_not_a_separate_execution_action():
    from doc_tasks.extract import kind_options
    assert "execution_reporting" not in kind_options("Bo‘lim topshiriqlar ijrosi to‘g‘risida har oyda axborot kiritsin.")
    assert "execution_reporting" in kind_options("Topshiriqlar bajarilishini ta’minlash hamda har oyda axborot kiritib borishingizni so‘raymiz.")
