"""GET /api/lead-data - Get lead data for a session (demo view)."""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from urllib.parse import parse_qs, urlparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg
from psycopg.rows import dict_row

from api.session import get_db_url, load_session


def get_lead_data(lead_id: int = None, email: str = None, phone: str = None) -> dict | None:
    """Get lead record from database by lead_id or email/phone."""
    db_url = get_db_url()
    if not db_url:
        return None

    try:
        with psycopg.connect(db_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Try by lead_id first
                if lead_id:
                    cur.execute(
                        "SELECT * FROM rrc_leads WHERE lead_id = %s",
                        (lead_id,)
                    )
                    row = cur.fetchone()
                    if row:
                        return {k: (str(v) if v is not None else None) for k, v in dict(row).items()}

                # Try by email
                if email:
                    cur.execute(
                        "SELECT * FROM rrc_leads WHERE LOWER(email) = LOWER(%s)",
                        (email,)
                    )
                    row = cur.fetchone()
                    if row:
                        return {k: (str(v) if v is not None else None) for k, v in dict(row).items()}

                # Try by phone (normalize)
                if phone:
                    normalized_phone = "".join(c for c in phone if c.isdigit())
                    cur.execute(
                        """
                        SELECT * FROM rrc_leads
                        WHERE REGEXP_REPLACE(mobile_phone, '[^0-9]', '', 'g') = %s
                        """,
                        (normalized_phone,)
                    )
                    row = cur.fetchone()
                    if row:
                        return {k: (str(v) if v is not None else None) for k, v in dict(row).items()}

    except Exception as e:
        print(f"Error fetching lead data: {e}")

    return None


# Field groups for display organization
FIELD_GROUPS = [
    {
        "name": "Identity",
        "fields": [
            ("email", "Email"),
            ("mobile_phone", "Phone"),
        ]
    },
    {
        "name": "Demographics",
        "fields": [
            ("first_name", "First Name"),
            ("last_name", "Last Name"),
            ("date_of_birth", "Date of Birth"),
            ("gender", "Gender"),
        ]
    },
    {
        "name": "Address",
        "fields": [
            ("address_line1", "Street Address"),
            ("city", "City"),
            ("state", "State"),
            ("zip_code", "ZIP Code"),
        ]
    },
    {
        "name": "Study Info",
        "fields": [
            ("has_smartphone", "Has Smartphone"),
            ("advertisement_source", "Ad Source"),
            ("closest_rrc_site", "Closest Site"),
        ]
    },
    {
        "name": "Nicotine Use",
        "fields": [
            ("nicotine_products_used", "Products Used"),
            ("cigarettes_menthol", "Menthol Cigarettes"),
            ("cigarettes_years", "Years Smoking"),
            ("cigarettes_days_per_week", "Days/Week"),
            ("cigarettes_per_day", "Cigarettes/Day"),
            ("cigarettes_brand", "Cigarette Brand"),
        ]
    },
    {
        "name": "Health",
        "fields": [
            ("pregnant_or_nursing_or_planning", "Pregnant/Nursing"),
            ("height_feet", "Height (ft)"),
            ("height_inches", "Height (in)"),
            ("weight_lbs", "Weight (lbs)"),
            ("alcohol_frequency", "Alcohol Frequency"),
            ("willing_urine_drug_screen", "Drug Screen OK"),
            ("serious_medical_conditions", "Medical Conditions"),
            ("medications_last_30_days", "Medications"),
        ]
    },
]


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Parse query params
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            session_id = params.get("session_id", [None])[0]

            if not session_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "session_id required"}).encode())
                return

            # Load session to get lead_id
            session_data = load_session(session_id)
            if not session_data:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Session not found"}).encode())
                return

            study_id, state = session_data

            # Get lead_id from state (try multiple places)
            lead_record = state.get("lead_record", {}) or {}
            lead_id = lead_record.get("lead_id")

            # Get identity info for fallback lookup
            lead_identity = state.get("lead_identity", {}) or {}
            email = lead_identity.get("email") or lead_record.get("email")
            phone = lead_identity.get("phone") or lead_record.get("mobile_phone")

            # Fetch current lead data from DB (try lead_id first, then email/phone)
            lead_data = get_lead_data(lead_id=lead_id, email=email, phone=phone)

            # Get missing fields from state
            missing_fields = set(state.get("missing_fields", []))

            # Get lead_id from lead_data if we found a record
            if lead_data and not lead_id:
                lead_id = lead_data.get("lead_id")

            response = {
                "session_id": session_id,
                "lead_id": int(lead_id) if lead_id else None,
                "current_step": state.get("current_step", ""),
                "lead_data": lead_data,
                "missing_fields": list(missing_fields),
                "field_groups": FIELD_GROUPS,
            }

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
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
