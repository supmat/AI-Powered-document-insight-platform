import spacy
from spacy.util import is_package
from langdetect import detect, DetectorFactory

# Enforce deterministic language detection
DetectorFactory.seed = 0

# Map ISO language codes to respective SpaCy NER models
LANGUAGE_MODEL_MAP = {
    "en": "en_core_web_sm",
    "de": "de_core_news_sm",
    "es": "es_core_news_sm",
    "fr": "fr_core_news_sm",
    "it": "it_core_news_sm",
    "nl": "nl_core_news_sm",
    "pt": "pt_core_news_sm",
}

# Cache loaded NLP models in memory to prevent reloading
loaded_models = {}


def get_spacy_model(lang_code: str):
    # xx_ent_wiki_sm is the Official SpaCy Multi-language strictly-NER model
    model_name = LANGUAGE_MODEL_MAP.get(lang_code, "xx_ent_wiki_sm")

    if model_name not in loaded_models:
        if not is_package(model_name):
            print(
                f"[*] Dynamically downloading SpaCy NLP model: {model_name} for language '{lang_code}'..."
            )
            spacy.cli.download(model_name)

        nlp = spacy.load(model_name)

        if not nlp.has_pipe("code_entity_ruler"):
            # Add it BEFORE the statistical NER so it takes priority
            ruler = nlp.add_pipe("entity_ruler", name="code_entity_ruler", before="ner")
            patterns = [
                {
                    "label": "CODE",
                    "pattern": [{"TEXT": {"REGEX": r"^[A-Z0-9]{2,}(?:-[A-Z0-9]+)+$"}}],
                }
            ]
            ruler.add_patterns(patterns)

        loaded_models[model_name] = nlp

    return loaded_models[model_name]


def extract_entities(text: str) -> list[dict]:
    """
    Extracts named entities from text by dynamically detecting the native language
    and routing text to the localized SpaCy model.
    """
    try:
        lang = detect(text)
    except Exception:
        lang = "en"  # Absolute fallback

    nlp = get_spacy_model(lang)
    doc = nlp(text)

    entities = []
    seen = set()
    allowed_labels = {
        "PERSON",
        "PER",
        "ORG",
        "GPE",
        "LOC",
        "PRODUCT",
        "EVENT",
        "DATE",
        "MISC",
        "CODE",
    }

    for ent in doc.ents:
        # Multi-lang models use 'PER'/'MISC' whereas English uses 'PERSON'
        if ent.label_ in allowed_labels:
            clean_text = ent.text.strip()
            ent_val_lower = (clean_text.lower(), ent.label_)

            if ent_val_lower not in seen:
                seen.add(ent_val_lower)
                entities.append({"text": clean_text, "label": ent.label_})
            elif ent.label_ == "PER" and "PERSON" not in [e["label"] for e in entities]:
                # If we only saw "PER" but not "PERSON" yet, add the "PERSON" variant too
                entities.append({"text": clean_text, "label": "PERSON"})

            if ent_val_lower not in seen and len(clean_text) > 1:
                seen.add(ent_val_lower)
                entities.append({"text": clean_text, "label": ent.label_})

    return entities
