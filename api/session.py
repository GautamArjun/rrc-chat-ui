"""POST /api/session - Create a new chat session."""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import uuid

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg
from psycopg.rows import dict_row


def get_db_url():
    return os.environ.get("DATABASE_URL")


def save_session(session_id: str, study_id: str, state: dict):
    """Save session state to database."""
    with psycopg.connect(get_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rrc_sessions (session_id, study_id, state)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE
                SET state = EXCLUDED.state, updated_at = NOW()
                """,
                (session_id, study_id, json.dumps(state, default=str))
            )
            conn.commit()


def load_session(session_id: str):
    """Load session state from database."""
    with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT study_id, state FROM rrc_sessions WHERE session_id = %s",
                (session_id,)
            )
            row = cur.fetchone()
            if row:
                return row["study_id"], json.loads(row["state"])
    return None


def state_to_response(session_id: str, state: dict) -> dict:
    """Convert agent state to API response."""
    step = state.get("current_step", "")

    # Determine response type
    terminal_steps = {"consent_declined", "auth_fail_handoff", "qualified_handoff", "disqualified"}
    resp_type = "end" if step in terminal_steps else "text"

    # Get last assistant message
    message = ""
    for msg in reversed(state.get("messages", [])):
        if msg["role"] == "assistant":
            message = msg["content"]
            break

    # Determine fields and options
    fields = None
    options = None
    field = None

    # Identity form
    if step in ("consent_given", "collecting_identity"):
        resp_type = "form"
        fields = [
            {"name": "email", "type": "email", "label": "Email address"},
            {"name": "phone", "type": "tel", "label": "Phone number"},
        ]

    # PIN input
    elif step == "awaiting_pin":
        resp_type = "form"
        field = "pin"

    # Scheduling form
    elif step == "scheduling":
        resp_type = "form"
        fields = [
            {
                "name": "preferred_days",
                "type": "multi_select",
                "label": "Preferred days",
                "options": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            },
            {
                "name": "preferred_times",
                "type": "multi_select",
                "label": "Preferred time of day",
                "options": ["Morning (9am-12pm)", "Afternoon (12pm-5pm)", "Evening (5pm-8pm)"],
            },
        ]

    # Profile form groups
    elif step.startswith("collecting_group:"):
        resp_type = "form"
        from rrcagent.nodes import PROFILE_FIELD_GROUPS
        group_name = step.split(":", 1)[1]
        missing_set = set(state.get("missing_fields", []))

        field_types = {
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

        select_options = {
            "gender": ["Male", "Female", "Non-binary", "Prefer not to say"],
            "has_smartphone": ["Yes", "No"],
            "closest_rrc_site": ["Raleigh", "Charlotte"],
            "pregnant_or_nursing_or_planning": ["Yes", "No"],
            "willing_urine_drug_screen": ["Yes", "No"],
        }

        fields = []
        for group in PROFILE_FIELD_GROUPS:
            if group["name"] == group_name:
                for f in group["fields"]:
                    if f in missing_set:
                        ftype, flabel = field_types.get(f, ("text", f.replace("_", " ").title()))
                        field_def = {"name": f, "type": ftype, "label": flabel}
                        if f in select_options:
                            field_def["options"] = select_options[f]
                        fields.append(field_def)
                break

    # Prescreen questions
    elif step.startswith("prescreen:"):
        study_config = state.get("study_config", {})
        questions = study_config.get("pre_screen", {}).get("questions", [])
        q_id = step.split(":", 1)[1]
        for q in questions:
            if q["id"] == q_id and q.get("type") == "yes_no":
                resp_type = "form"
                options = ["Yes", "No"]
                break

    # If we have fields or options, it's a form
    if fields is not None or options is not None:
        resp_type = "form" if resp_type != "end" else "end"

    return {
        "session_id": session_id,
        "message": message,
        "type": resp_type,
        "step": step,
        "field": field,
        "fields": fields,
        "options": options,
        "done": resp_type == "end",
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body) if body else {}
            study_id = data.get("study_id", "zyn")

            # Import agent modules
            from rrcagent.config import load_study_config
            from rrcagent.graph import step_graph, build_graph
            from rrcagent.db import Database

            # Load study config
            study_config = load_study_config(study_id)

            # Create services
            db = Database(get_db_url())
            services = {"db": db}

            # Build graph and run greeting
            graph = build_graph(services)
            state = step_graph(
                graph,
                study_id=study_id,
                study_config=study_config,
                services=services,
            )

            # Generate session ID and save
            session_id = str(uuid.uuid4())
            save_session(session_id, study_id, state)

            # Build response
            response = state_to_response(session_id, state)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            import traceback
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e), "trace": traceback.format_exc()}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
