"""
rag_integration.py
-------------------
Lightweight keyword-based knowledge retrieval for the voice assistant.

WHAT IS RAG?
    RAG = Retrieval-Augmented Generation.
    The idea: instead of asking the LLM to answer everything from training
    data alone, you first *retrieve* relevant facts from your own knowledge
    base, then *inject* them into the prompt so the LLM answers with
    accurate, domain-specific information.

    Full RAG systems use vector embeddings and semantic search (e.g. FAISS,
    Pinecone). This is a simplified keyword-based version — fast, zero
    dependencies, and good enough for a focused real estate domain.

HOW IT WORKS HERE:
    1. Caller says something → assistant.py calls get_relevant_context(query)
    2. We check if any keyword from KNOWLEDGE_BASE appears in the query
    3. If yes → return that topic's answer to inject into the LLM prompt
    4. LLM uses it as grounding context when forming its reply

    Example:
        Query:   "what documents do I need?"
        Match:   topic "documents" (keyword "document" found)
        Injected into prompt → LLM answers accurately about Aadhaar, PAN etc.

WHY RETURN ONLY THE FIRST MATCH?
    Voice responses need to be short. One focused answer is better than
    several partial answers stitched together. The most relevant topic
    is enough grounding for the LLM to respond well.
"""

# ------------------------------------------------------------------
# KNOWLEDGE BASE
# ------------------------------------------------------------------

# Each entry covers one real estate topic.
# keywords  → trigger words to detect in the caller's query
# answer    → factual context injected into the LLM prompt (not spoken directly)
KNOWLEDGE_BASE = [
    {
        "topic": "buying process",
        "keywords": ["buy", "purchase", "booking", "process"],
        "answer": (
            "For buying, we collect your city, budget, property type, purpose, "
            "and phone number. Then we suggest matching properties and arrange expert callback."
        ),
    },
    {
        "topic": "rent process",
        "keywords": ["rent", "rental", "lease"],
        "answer": (
            "For rental property, we need your city, monthly budget, "
            "preferred home type, and move-in timeline."
        ),
    },
    {
        "topic": "loan",
        "keywords": ["loan", "emi", "finance", "bank"],
        "answer": (
            "Home loan support can be arranged. The expert can guide about "
            "EMI, down payment, eligibility, and documents."
        ),
    },
    {
        "topic": "site visit",
        "keywords": ["visit", "site", "tour", "see property"],
        "answer": (
            "A site visit can be arranged after shortlisting the property. "
            "Our team can coordinate the visit timing."
        ),
    },
    {
        "topic": "documents",
        "keywords": ["document", "papers", "agreement", "registration"],
        "answer": (
            "Common documents include Aadhaar, PAN, income proof, bank statement, "
            "agreement papers, and registration documents."
        ),
    },
    {
        "topic": "investment",
        "keywords": ["investment", "invest", "return", "rental income"],
        "answer": (
            "For investment, we suggest locations with good connectivity, "
            "upcoming development, and rental demand."
        ),
    },
]


# ------------------------------------------------------------------
# RETRIEVAL
# ------------------------------------------------------------------

def get_relevant_context(query: str) -> str:
    """
    Find and return the most relevant knowledge base answer for a query.

    Called by assistant.py when all profile fields are collected and the
    caller asks a free-form question. The returned string is injected into
    the LLM prompt under "Relevant real estate knowledge:" so the model
    can ground its answer in domain-specific facts.

    Parameters
    ----------
    query : str
        The caller's raw message text.

    Returns
    -------
    str
        The answer string for the first matching topic, or "" if nothing
        matches. An empty string is safe — the LLM prompt handles it
        gracefully (the section just has no extra context).

    HOW MATCHING WORKS:
        Simple substring check — if any keyword appears anywhere in the
        lowercased query, that topic matches.

        "what documents do I need for purchase?"
            → matches "documents" topic (keyword "document" found)
            → also would match "buying" (keyword "purchase" found)
            → returns "documents" because it appears first in KNOWLEDGE_BASE

    LIMITATION TO KNOW FOR INTERVIEW:
        Order in KNOWLEDGE_BASE determines priority — not relevance.
        "process for purchase of documents" would return "buying process"
        even though "documents" is arguably more relevant.
        A real RAG system would score all matches and return the best one.
        For this project scope, first-match is fast and good enough.
    """
    query = (query or "").lower()

    for item in KNOWLEDGE_BASE:
        for keyword in item["keywords"]:
            if keyword in query:
                return item["answer"]   # return on first match — enough context for one reply

    return ""   # no match — LLM will answer from its own training data