import spacy
import re
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

        loaded_models[model_name] = spacy.load(model_name)

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
    for ent in doc.ents:
        # Multi-lang models use 'PER'/'MISC' whereas English uses 'PERSON'
        if ent.label_ in [
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
        ]:
            ent_val = (ent.text.strip(), ent.label_)
            if ent_val not in seen:
                seen.add(ent_val)
                entities.append({"text": ent.text.strip(), "label": ent.label_})

    # 2. Add regex-based 'CODE' entities that standard tokenizers often split
    # This captures things like: 42-ALPHA-ZULU, UUIDs, or PROJECT-123-X
    code_pattern = r"\b[A-Z0-9]{2,}(?:-[A-Z0-9]+)+\b"
    for match in re.finditer(code_pattern, text):
        code_text = match.group().strip()
        ent_val = (code_text, "CODE")
        if ent_val not in seen:
            seen.add(ent_val)
            entities.append({"text": code_text, "label": "CODE"})

    return entities
