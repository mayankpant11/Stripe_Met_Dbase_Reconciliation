"""Word-overlap retrieval for runbook documents stored in Supabase."""

import math

from tools import get_docs


def cosine_sim(query: str, content: str) -> float:
    """Score two strings by cosine similarity over their unique words."""
    query_words = set(query.lower().split())
    content_words = set(content.lower().split())
    overlap = len(query_words & content_words)
    denominator = math.sqrt(len(query_words) * len(content_words))
    return overlap / (denominator + 1e-6)


def retrieve_top3(query: str, threshold: float = 0.2) -> list[tuple[dict, float]]:
    """Return up to three matching runbook docs, highest score first."""
    documents = get_docs()
    scored = [
        (document, cosine_sim(query, f"{document['content']} {document['title']}"))
        for document in documents
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return [(document, score) for document, score in scored[:3] if score >= threshold]
