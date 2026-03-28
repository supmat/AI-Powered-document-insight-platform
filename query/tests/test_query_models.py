from query.models.query import QueryRequest, SourceQuote, QueryResponse


def test_query_request_model():
    req = QueryRequest(question="What is this?", top_k=3)
    assert req.question == "What is this?"
    assert req.top_k == 3


def test_source_quote_model():
    quote = SourceQuote(document_id="doc1", filename="test.pdf", text_snippet="hello")
    assert quote.document_id == "doc1"
    assert quote.filename == "test.pdf"
    assert quote.text_snippet == "hello"


def test_query_response_model():
    quote = SourceQuote(document_id="doc1", filename="test.pdf", text_snippet="hello")
    resp = QueryResponse(
        answer="It is a test.",
        confidence_score=0.9,
        quoted_sources=[quote],
        detected_entities=["test"],
    )
    assert resp.answer == "It is a test."
    assert resp.confidence_score == 0.9
    assert len(resp.quoted_sources) == 1
    assert resp.detected_entities == ["test"]
