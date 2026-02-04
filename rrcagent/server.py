"""FastAPI chat server for the RRC recruitment agent.

Provides REST endpoints for session management and turn-by-turn conversation.
"""

from __future__ import annotations

import pathlib
import re
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rrcagent.config import load_study_config
from rrcagent.graph import step_graph, build_graph


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SessionRequest(BaseModel):
    study_id: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class FieldDescriptor(BaseModel):
    name: str
    type: str
    label: str
    options: list[str] | None = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    type: str          # "text", "form", or "end"
    step: str
    field: str | None = None
    fields: list[FieldDescriptor] | None = None
    options: list[str] | None = None
    done: bool = False


# ---------------------------------------------------------------------------
# FAQ detection
# ---------------------------------------------------------------------------

_QUESTION_WORD_RE = re.compile(
    r"^\s*(what|how|when|where|why|who|can|is|does|do|will|are|could|would|should|tell me)\b",
    re.IGNORECASE,
)


def _is_faq_question(message: str) -> bool:
    """Detect if a user message looks like a general FAQ question."""
    text = message.strip()
    # Too short to be a real question
    if len(text) < 10:
        return False
    # JSON form submissions are never FAQ questions
    if text.startswith("{"):
        return False
    # Ends with "?" and long enough
    if text.endswith("?") and len(text) >= 15:
        return True
    # Starts with a question word and is long enough
    if _QUESTION_WORD_RE.match(text) and len(text) >= 20:
        return True
    return False


# ---------------------------------------------------------------------------
# Terminal steps — conversation is over
# ---------------------------------------------------------------------------

_TERMINAL_STEPS = {
    "consent_declined",
    "auth_fail_handoff",
    "qualified_handoff",
    "disqualified",
}


# ---------------------------------------------------------------------------
# State -> response helpers
# ---------------------------------------------------------------------------

def _last_assistant_message(state: dict) -> str:
    """Extract the last assistant message from state."""
    for msg in reversed(state.get("messages", [])):
        if msg["role"] == "assistant":
            return msg["content"]
    return ""


def _determine_type(state: dict) -> str:
    """Determine the response type from state."""
    step = state.get("current_step", "")
    if step in _TERMINAL_STEPS:
        return "end"
    return "text"


def _determine_field(state: dict) -> str | None:
    """Extract the field name if currently collecting a profile field."""
    step = state.get("current_step", "")
    if step.startswith("collecting:"):
        return step.split(":", 1)[1]
    return None


_IDENTITY_FIELDS = [
    FieldDescriptor(name="email", type="email", label="Email address"),
    FieldDescriptor(name="phone", type="tel", label="Phone number"),
]

# Field type mappings for profile form rendering
_PROFILE_FIELD_TYPES = {
    "first_name": ("text", "First name"),
    "last_name": ("text", "Last name"),
    "date_of_birth": ("date", "Date of birth"),
    "gender": ("select", "Gender"),
    "address_line1": ("text", "Street address"),
    "city": ("text", "City"),
    "state": ("text", "State"),
    "zip_code": ("text", "ZIP code"),
    "has_smartphone": ("select", "Do you have a smartphone?"),
    "advertisement_source": ("text", "How did you hear about this study?"),
    "closest_rrc_site": ("select", "Closest RRC site"),
    "nicotine_products_used": ("text", "Nicotine products used"),
    "pregnant_or_nursing_or_planning": ("select", "Pregnant, nursing, or planning?"),
    "height_feet": ("number", "Height (feet)"),
    "height_inches": ("number", "Height (inches)"),
    "weight_lbs": ("number", "Weight (lbs)"),
    "alcohol_frequency": ("text", "How often do you drink alcohol?"),
    "alcohol_quantity": ("text", "Drinks per occasion"),
    "willing_urine_drug_screen": ("select", "Willing to do a urine drug screen?"),
    "serious_medical_conditions": ("text", "Serious medical conditions"),
    "medications_last_30_days": ("text", "Medications in last 30 days"),
}


_SCHEDULING_FIELDS = [
    FieldDescriptor(
        name="preferred_days",
        type="multi_select",
        label="Preferred days",
        options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    ),
    FieldDescriptor(
        name="preferred_times",
        type="multi_select",
        label="Preferred time of day",
        options=["Morning (9am-12pm)", "Afternoon (12pm-5pm)", "Evening (5pm-8pm)"],
    ),
]


def _determine_fields(state: dict) -> list[FieldDescriptor] | None:
    """Return a list of field descriptors for multi-field form steps."""
    step = state.get("current_step", "")
    if step in ("consent_given", "collecting_identity"):
        return _IDENTITY_FIELDS
    if step == "scheduling":
        return _SCHEDULING_FIELDS
    if step.startswith("collecting_group:"):
        group_name = step.split(":", 1)[1]
        from rrcagent.nodes import PROFILE_FIELD_GROUPS
        missing_set = set(state.get("missing_fields", []))
        for group in PROFILE_FIELD_GROUPS:
            if group["name"] == group_name:
                fields = []
                for f in group["fields"]:
                    if f in missing_set:
                        ftype, flabel = _PROFILE_FIELD_TYPES.get(f, ("text", f.replace("_", " ").title()))
                        fields.append(FieldDescriptor(name=f, type=ftype, label=flabel))
                return fields if fields else None
    return None


def _determine_options(state: dict) -> list[str] | None:
    """Determine options for form-type responses."""
    step = state.get("current_step", "")
    if step.startswith("prescreen:"):
        # Check if the current prescreen question has yes/no type
        questions = state.get("study_config", {}).get("pre_screen", {}).get("questions", [])
        q_id = step.split(":", 1)[1]
        for q in questions:
            if q["id"] == q_id and q.get("type") == "yes_no":
                return ["Yes", "No"]
    field = _determine_field(state)
    if field == "has_smartphone":
        return ["Yes", "No"]
    if field == "pregnant_or_nursing_or_planning":
        return ["Yes", "No"]
    if field == "willing_urine_drug_screen":
        return ["Yes", "No"]
    if field == "gender":
        return ["Male", "Female", "Non-binary", "Prefer not to say"]
    if field == "closest_rrc_site":
        return ["Raleigh", "Charlotte"]
    if field == "state":
        return None  # Too many to list as options, use text input
    return None


def _state_to_response(session_id: str, state: dict) -> ChatResponse:
    """Convert agent state into a ChatResponse."""
    step = state.get("current_step", "")
    resp_type = _determine_type(state)
    field = _determine_field(state)
    fields = _determine_fields(state)
    options = _determine_options(state)

    # If there's a field, fields, or options, it's a form type
    if field is not None or fields is not None or options is not None:
        resp_type = "form" if resp_type != "end" else "end"

    return ChatResponse(
        session_id=session_id,
        message=_last_assistant_message(state),
        type=resp_type,
        step=step,
        field=field,
        fields=fields,
        options=options,
        done=resp_type == "end",
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(
    services: dict | None = None,
    study_id: str = "zyn",
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        services: Dict with db, embedder, store, llm for dependency injection.
        study_id: Default study to load config for.
    """
    app = FastAPI(title="RRC Agent Chat")

    # Load study config
    try:
        study_config = load_study_config(study_id)
    except Exception:
        study_config = None

    # Build graph (for validation)
    graph = build_graph(services)

    # In-memory session store
    sessions: dict[str, dict] = {}

    @app.post("/session", response_model=ChatResponse)
    def create_session(req: SessionRequest):
        sid = str(uuid.uuid4())

        # Load config for requested study
        try:
            config = load_study_config(req.study_id)
        except Exception:
            config = study_config
            if config is None:
                raise HTTPException(status_code=400, detail="Unknown study ID")

        # Initialize state — runs greeting node
        state = step_graph(
            graph,
            study_id=req.study_id,
            study_config=config,
            services=services,
        )

        sessions[sid] = state
        return _state_to_response(sid, state)

    @app.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest):
        state = sessions.get(req.session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Session not found")

        # If conversation is already done, return current state
        if state.get("current_step", "") in _TERMINAL_STEPS:
            return _state_to_response(req.session_id, state)

        # FAQ interrupt — detect questions and route to RAG
        rag = (services or {}).get("rag")
        if rag and _is_faq_question(req.message):
            result = rag.answer(req.message, state.get("study_id", ""))
            return ChatResponse(
                session_id=req.session_id,
                message=result["text"],
                type="text",
                step=state.get("current_step", ""),
                done=False,
            )

        # Step the graph with user message
        state = step_graph(
            graph,
            state=state,
            user_message=req.message,
            services=services,
        )

        sessions[req.session_id] = state
        return _state_to_response(req.session_id, state)

    # Static files and index route
    static_dir = pathlib.Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/")
        def index():
            return FileResponse(str(static_dir / "index.html"))

    return app
