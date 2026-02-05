"""RAG utilities for the Vercel API."""

import os
import re
from pathlib import Path


def get_google_api_key():
    """Get Google API key from environment."""
    return os.environ.get("GOOGLE_API_KEY")


def get_faq_path(study_id: str) -> str:
    """Get the path to the FAQ document for a study."""
    # Calculate path relative to this file
    api_dir = Path(__file__).resolve().parent
    project_root = api_dir.parent
    return str(project_root / "studies" / study_id / "faq.md")


def is_faq_question(message: str) -> bool:
    """Detect if a message is likely an FAQ question.

    Returns True for questions that should be routed to RAG.
    Returns False for form submissions, short responses, or workflow answers.
    """
    if not message:
        return False

    message = message.strip()

    # Skip JSON (form submissions)
    if message.startswith("{") or message.startswith("["):
        return False

    # Skip very short messages (likely yes/no responses)
    if len(message) < 10:
        return False

    # Check for question mark with reasonable length
    if message.endswith("?") and len(message) >= 15:
        return True

    # Check for question words at start
    question_starters = (
        "what", "how", "when", "where", "why", "who", "which",
        "can i", "do i", "will i", "is there", "are there",
        "tell me", "explain", "describe"
    )
    lower_msg = message.lower()
    for starter in question_starters:
        if lower_msg.startswith(starter) and len(message) >= 20:
            return True

    return False


def init_rag_service(study_id: str):
    """Initialize the RAG service for a study.

    Returns the RagService instance, or None if initialization fails.
    """
    api_key = get_google_api_key()
    if not api_key:
        return None

    try:
        from rrcagent.rag.embedder import GeminiEmbedder
        from rrcagent.rag.store import MockVectorStore
        from rrcagent.rag.llm import GeminiLLM
        from rrcagent.rag.service import RagService

        # Initialize components
        embedder = GeminiEmbedder(api_key=api_key)
        store = MockVectorStore()
        llm = GeminiLLM(api_key=api_key)

        # Create service
        rag = RagService(embedder=embedder, store=store, llm=llm, top_k=3)

        # Index the FAQ document
        faq_path = get_faq_path(study_id)
        if os.path.exists(faq_path):
            rag.index_document(study_id, faq_path)

        return rag
    except Exception as e:
        print(f"Failed to initialize RAG: {e}")
        return None


def answer_faq(rag, question: str, study_id: str, current_step: str, session_id: str) -> dict:
    """Answer an FAQ question using RAG.

    Returns a response dict in the same format as state_to_response.
    """
    try:
        result = rag.answer(question, study_id)
        return {
            "session_id": session_id,
            "message": result.get("text", "I don't have information about that in the study FAQ."),
            "type": "text",
            "step": current_step,  # Stay on current step
            "field": None,
            "fields": None,
            "options": None,
            "done": False,
        }
    except Exception as e:
        print(f"RAG answer failed: {e}")
        return {
            "session_id": session_id,
            "message": "I'm sorry, I couldn't find that information. Please continue with the screening process, or feel free to ask another question.",
            "type": "text",
            "step": current_step,
            "field": None,
            "fields": None,
            "options": None,
            "done": False,
        }
