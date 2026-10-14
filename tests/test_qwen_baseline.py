import json

import httpx

from doc_tasks.decisions import DecisionQuestion, QwenDecisions


def test_qwen_baseline_is_text_only_and_constrained():
    def handle(request):
        payload = json.loads(request.content)
        assert payload["think"] is False
        assert all("images" not in message for message in payload["messages"])
        assert payload["format"]["properties"]["q"]["enum"] == ["yes", "no"]
        return httpx.Response(200, json={"message": {"content": '{"q":"yes"}'}})
    client = QwenDecisions("qwen3.5:4b", transport=httpx.MockTransport(handle))
    result = client.evaluate({"text": "Launch module"}, [
        DecisionQuestion(id="q", type="noul", instructions="Is this an obligation?")
    ])
    assert result["q"].selected_id == "yes"
    assert result["q"].raw_confidence is None
