"""GreenLens LM — API endpoint tests"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)

MOCK_RESPONSE = {
    "answer": "Indonesia's unconditional target is 31.89% under Enhanced NDC 2022.",
    "sources": [{
        "content": "Sample NDC content.",
        "source_file": "ndc/enhanced-ndc-2022-en.pdf",
        "regulation": "Enhanced NDC 2022",
        "category": "climate_commitment",
        "year": 2022,
        "page": 5,
    }],
    "model_used": "openai/gpt-oss-20b:free",
}


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "GreenLens" in r.json()["name"]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert "status" in r.json()


def test_query_empty_rejected():
    r = client.post("/api/query", json={"question": ""})
    assert r.status_code == 422


def test_query_too_long_rejected():
    r = client.post("/api/query", json={"question": "x" * 2001})
    assert r.status_code == 422


def test_query_invalid_language():
    r = client.post("/api/query", json={"question": "test", "language": "fr"})
    assert r.status_code == 422


# Mock at the router level — where get_rag_response is imported and called
@patch("app.routers.query.get_rag_response", new_callable=AsyncMock)
def test_query_success(mock_rag):
    mock_rag.return_value = MOCK_RESPONSE
    r = client.post("/api/query", json={"question": "What is Indonesia's emission target?"})
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "sources" in data
    assert "31.89" in data["answer"]


@patch("app.routers.query.get_rag_response", new_callable=AsyncMock)
def test_query_with_category(mock_rag):
    mock_rag.return_value = MOCK_RESPONSE
    r = client.post("/api/query", json={
        "question": "Apa itu AMDAL?", "language": "id", "category": "environmental_law"
    })
    assert r.status_code == 200
    call_kwargs = mock_rag.call_args.kwargs
    assert call_kwargs["category_filter"] == "environmental_law"
    assert call_kwargs["language"] == "id"


@patch("app.routers.query.get_rag_response", new_callable=AsyncMock)
def test_query_with_chat_history(mock_rag):
    mock_rag.return_value = MOCK_RESPONSE
    r = client.post("/api/query", json={
        "question": "Tell me more",
        "chat_history": [
            {"role": "user", "content": "What is NDC?"},
            {"role": "assistant", "content": "NDC is..."},
        ]
    })
    assert r.status_code == 200


def test_ingest_status():
    r = client.get("/api/ingest/status")
    assert r.status_code == 200
    assert "running" in r.json()


@patch("app.routers.query.get_rag_response", new_callable=AsyncMock)
def test_query_rate_limit_enforced(mock_rag):
    """Integration check that the rate limiter dependency is actually
    wired to /api/query. Temporarily lowers the limit and resets state
    so this test doesn't depend on (or pollute) other tests' request
    counts against the shared TestClient host."""
    from app.rate_limiter import rate_limiter

    mock_rag.return_value = MOCK_RESPONSE
    original_max = rate_limiter.max_requests
    rate_limiter.max_requests = 2
    rate_limiter._requests.clear()

    try:
        r1 = client.post("/api/query", json={"question": "first"})
        r2 = client.post("/api/query", json={"question": "second"})
        r3 = client.post("/api/query", json={"question": "third"})

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429
        assert "Retry-After" in r3.headers
    finally:
        rate_limiter.max_requests = original_max
        rate_limiter._requests.clear()
