"""POST /api/chat - Send a message in an existing session."""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.session import get_db_url, load_session, save_session, state_to_response
from api.rag_utils import is_faq_question, init_rag_service, answer_faq


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body) if body else {}

            session_id = data.get("session_id")
            message = data.get("message", "")

            if not session_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "session_id required"}).encode())
                return

            # Load session
            session_data = load_session(session_id)
            if not session_data:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Session not found"}).encode())
                return

            study_id, state = session_data

            # Check if this is an FAQ question - route to RAG without advancing state
            if is_faq_question(message):
                rag = init_rag_service(study_id)
                if rag:
                    current_step = state.get("current_step", "")
                    response = answer_faq(rag, message, study_id, current_step, session_id)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())
                    return

            # Import agent modules
            from rrcagent.graph import step_graph, build_graph
            from rrcagent.db import Database

            # Create services
            db = Database(get_db_url())
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
