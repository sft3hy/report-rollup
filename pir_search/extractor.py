import re
import spacy
from keybert import KeyBERT

# Global caches for lazy loading
_nlp = None
_kw_model = None

# Regex to strip common fillers, question words, and metadata words
FILLER_RE = re.compile(
    r"\b(what|who|where|why|how|is|are|was|were|the|a|an|in|on|at|to|for|with|about|against|of|and|or|but|doing|targeting|current|status|latest|recent|pir|requirement|intelligence|priority|activities|activity|report|reports|brief|updates?|findings?)\b",
    re.IGNORECASE
)

def get_spacy_model():
    """Lazy-loads and returns the spaCy model."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            # Fallback if download hasn't finished yet or fails
            _nlp = spacy.load("en_core_web_sm")
    return _nlp

def get_keybert_model(shared_transformer=None):
    """Lazy-loads and returns the KeyBERT model."""
    global _kw_model
    if _kw_model is None:
        if shared_transformer is not None:
            _kw_model = KeyBERT(model=shared_transformer)
        else:
            _kw_model = KeyBERT()
    return _kw_model

def clean_term(term: str) -> str:
    """Strips punctuation, filler words, and excess whitespace from a term."""
    # Convert to lowercase
    term = term.lower()
    # Remove filler words
    term = FILLER_RE.sub("", term)
    # Remove punctuation except hyphens/spaces
    term = re.sub(r"[^\w\s-]", "", term)
    # Normalize whitespace
    term = re.sub(r"\s+", " ", term).strip()
    return term

def extract_search_terms(pir: str, shared_transformer=None) -> list[str]:
    """
    Extracts 8-15 distinct search terms from a Priority Intelligence Requirement (PIR).
    Uses spaCy NER for hard keywords and KeyBERT for key noun phrases.
    """
    nlp = get_spacy_model()
    doc = nlp(pir)

    # 1. spaCy NER Extraction
    # Target entity types: GPE, ORG, PERSON, NORP, EVENT
    target_ents = {"GPE", "ORG", "PERSON", "NORP", "EVENT"}
    extracted_entities = set()
    for ent in doc.ents:
        if ent.label_ in target_ents:
            cleaned = clean_term(ent.text)
            if cleaned and len(cleaned) > 1:
                extracted_entities.add(cleaned)

    # 2. KeyBERT Keyword Extraction
    kw_model = get_keybert_model(shared_transformer)
    # Extract top 10 noun-phrase/n-gram candidates (1 to 2 words)
    keywords = kw_model.extract_keywords(
        pir,
        keyphrase_ngram_range=(1, 2),
        stop_words="english",
        top_n=10
    )
    
    extracted_keywords = set()
    for kw, _ in keywords:
        cleaned = clean_term(kw)
        if cleaned and len(cleaned) > 1:
            extracted_keywords.add(cleaned)

    # 3. Combine and Deduplicate
    all_terms = list(extracted_entities | extracted_keywords)

    # 4. Filter and clean candidates
    final_terms = []
    seen = set()
    for term in all_terms:
        # Extra check: ensure not empty, not already seen
        if term and term not in seen:
            seen.add(term)
            final_terms.append(term)

    # Ensure we have a reasonable number of search terms.
    # If we have too few, split multi-word terms to add unigrams, or add the clean PIR itself
    if len(final_terms) < 8:
        for term in list(final_terms):
            words = term.split()
            if len(words) > 1:
                for w in words:
                    w_cleaned = clean_term(w)
                    if w_cleaned and w_cleaned not in seen and len(w_cleaned) > 2:
                        seen.add(w_cleaned)
                        final_terms.append(w_cleaned)
        
        # If still less than 8, clean the entire PIR and add it
        pir_cleaned = clean_term(pir)
        if pir_cleaned and pir_cleaned not in seen:
            final_terms.append(pir_cleaned)

    # Cap at 15 to stay within limits
    return final_terms[:15]
