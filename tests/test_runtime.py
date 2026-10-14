import httpx
import pytest

from doc_tasks.decisions import DecisionUnavailable


def test_changed_weights_are_not_silently_accepted():
    from doc_tasks.runtime import verify_model_profile
    class Settings:
        model = "tev1:4b-q4_K_M"
        base_url = "http://127.0.0.1:11435"
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={
        "models": [{"name": Settings.model, "digest": "different-weights"}]}))
    with pytest.raises(DecisionUnavailable, match="digest"):
        verify_model_profile(Settings(), transport=transport)
