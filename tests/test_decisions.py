import httpx
import pytest

from doc_tasks.decisions import DecisionQuestion, DecisionUnavailable, OllamaDecisions


def test_tev1_uses_local_systemone_and_validates_choice():
    def handle(request):
        assert request.url.host == "127.0.0.1"
        assert request.url.path == "/v1/systemone"
        return httpx.Response(200, json={"answers": {"type": {
            "choice": "reporting", "probabilities": {"execution": .1, "reporting": .9}, "confidence": .8,
        }}})
    client = OllamaDecisions("tev1:0.8b", transport=httpx.MockTransport(handle))
    answer = client.evaluate({"text": "Submit a monthly report."}, [
        DecisionQuestion(id="type", type="choice", instructions="Select type",
                         options={"execution": "execution", "reporting": "reporting"})
    ])["type"]
    assert answer.selected_id == "reporting"
    assert answer.raw_confidence == .8


def test_unknown_model_choice_is_rejected():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={
        "answers": {"q": {"choice": "invented", "probabilities": {"a": .5, "b": .5}}}
    }))
    client = OllamaDecisions("tev1:4b", transport=transport)
    with pytest.raises(DecisionUnavailable):
        client.evaluate("text", [DecisionQuestion(id="q", type="choice", instructions="Select",
                                                  options={"a": "A", "b": "B"})])


def test_remote_inference_address_is_rejected():
    with pytest.raises(ValueError):
        OllamaDecisions("tev1:4b", base_url="https://example.com")
