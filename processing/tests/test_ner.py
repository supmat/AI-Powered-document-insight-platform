from processing.services.ner_client import extract_entities


def test_ner_extraction():
    text = "Apple is looking at buying U.K. startup for $1 billion in London."
    entities = extract_entities(text)

    entity_texts = [e["text"] for e in entities]
    assert "Apple" in entity_texts
    assert "U.K." in entity_texts
    assert "London" in entity_texts
