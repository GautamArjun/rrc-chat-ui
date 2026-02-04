"""POST /api/chat - Send a message in an existing session."""

import json
import os
from http.server import BaseHTTPRequestHandler

import psycopg
from psycopg.rows import dict_row

# Import the agent code
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rrcagent.graph import step_graph, build_graph
from rrcagent.db import Database

# Import state_to_response from session module
from api.session import state_to_response, save_session


def get_db():
    """Get database connection."""
    return Database(os.environ.get("DATABASE_URL"))


def load_session(session_id: str) -> tuple[str, dict] | None:
    """Load session state from database."""
    db_url = os.environ.get("DATABASE_URL")
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT study_id, state FROM rrc_sessions WHERE session_id = %s",
                (session_id,)
            )
            row = cur.fetchone()
            if row:
                return row["study_id"], json.loads(row["state"])
    return None


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
            session_id = data.get("session_id")
            message = data.get("message", "")

            if not session_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "session_id required"}).encode())
                return

            # Load session
            session_data = load_session(session_id)
            if not session_data:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Session not found"}).encode())
                return

            study_id, state = session_data

            # Create services
            db = get_db()
            services = {"db": db}

            # Build graph and step with user message
            graph = build_graph(services)
            state = step_graph(
                graph,
                state=state,
                user_message=message,
                services=services,
            )

            # Save updated state
            save_session(session_id, study_id, state)

            # Build response
            response = state_to_response(session_id, state)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
