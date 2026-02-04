"""PostgreSQL database operations for lead management.

Provides the Database class with methods for:
- lookup_lead: Find existing lead by email/phone
- create_lead: Create new lead record
- update_lead: Update lead fields
- create_handoff: Record agent-to-human handoff
"""

from __future__ import annotations

import json
import os
from typing import Protocol

import psycopg
from psycopg.rows import dict_row


class DatabaseProtocol(Protocol):
    """Protocol defining the database interface for dependency injection."""

    def lookup_lead(self, email: str, phone: str) -> dict | None:
        """Look up a lead by email or phone. Returns lead record or None."""
        ...

    def create_lead(self, identity: dict) -> int:
        """Create a new lead record. Returns the new lead_id."""
        ...

    def update_lead(self, lead_id: int, data: dict) -> None:
        """Update fields on an existing lead."""
        ...

    def create_handoff(self, lead_id: int, handoff_type: str, payload: dict) -> int:
        """Create a handoff record. Returns the handoff_id."""
        ...


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to digits only."""
    return "".join(c for c in phone if c.isdigit())


def _get_connection_string() -> str:
    """Get database connection string from environment or default."""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://localhost/rrcagent"
    )


class Database:
    """PostgreSQL database client for lead management."""

    def __init__(self, connection_string: str | None = None):
        """Initialize database connection.

        Args:
            connection_string: PostgreSQL connection string.
                Defaults to DATABASE_URL env var or localhost/rrcagent.
        """
        self._conninfo = connection_string or _get_connection_string()

    def _connect(self) -> psycopg.Connection:
        """Create a new database connection."""
        return psycopg.connect(self._conninfo, row_factory=dict_row)

    def lookup_lead(self, email: str, phone: str) -> dict | None:
        """Look up a lead by exact email OR phone match.

        Per guardrails: exact match only, never mix PHI across records.

        Args:
            email: Email address to search for.
            phone: Phone number to search for (will be normalized).

        Returns:
            Lead record as dict, or None if not found.
        """
        normalized_phone = _normalize_phone(phone)

        with self._connect() as conn:
            with conn.cursor() as cur:
                # Try email match first
                cur.execute(
                    "SELECT * FROM rrc_leads WHERE LOWER(email) = LOWER(%s)",
                    (email,)
                )
                row = cur.fetchone()
                if row:
                    return dict(row)

                # Try phone match (normalize stored phone for comparison)
                cur.execute(
                    """
                    SELECT * FROM rrc_leads
                    WHERE REGEXP_REPLACE(mobile_phone, '[^0-9]', '', 'g') = %s
                    """,
                    (normalized_phone,)
                )
                row = cur.fetchone()
                if row:
                    return dict(row)

        return None

    def create_lead(self, identity: dict) -> int:
        """Create a new lead record with email and phone.

        Args:
            identity: Dict with 'email' and 'phone' keys.

        Returns:
            The new lead_id.
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO rrc_leads (email, mobile_phone)
                    VALUES (%s, %s)
                    RETURNING lead_id
                    """,
                    (identity["email"], identity.get("phone"))
                )
                result = cur.fetchone()
                conn.commit()
                return result["lead_id"]

    def update_lead(self, lead_id: int, data: dict) -> None:
        """Update fields on an existing lead.

        Args:
            lead_id: The lead to update.
            data: Dict of field names to new values.
        """
        if not data:
            return

        # Build dynamic SET clause
        set_parts = []
        values = []
        for field, value in data.items():
            set_parts.append(f"{field} = %s")
            values.append(value)

        set_clause = ", ".join(set_parts)
        values.append(lead_id)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE rrc_leads
                    SET {set_clause}, updated_at = NOW()
                    WHERE lead_id = %s
                    """,
                    values
                )
                conn.commit()

    def create_handoff(self, lead_id: int, handoff_type: str, payload: dict) -> int:
        """Create a handoff record for agent-to-human transfer.

        Args:
            lead_id: The lead being handed off.
            handoff_type: One of 'AUTH_FAIL', 'QUALIFIED', 'OTHER'.
            payload: Additional data (e.g., preferred_times, reason).

        Returns:
            The new handoff_id.
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO rrc_handoffs (lead_id, handoff_type, payload)
                    VALUES (%s, %s, %s)
                    RETURNING handoff_id
                    """,
                    (lead_id, handoff_type, json.dumps(payload))
                )
                result = cur.fetchone()
                conn.commit()
                return result["handoff_id"]


class MockDatabase:
    """In-memory mock database for testing."""

    def __init__(self):
        self._leads: dict[str, dict] = {}
        self._handoffs: list[dict] = []
        self._next_lead_id = 1
        self._next_handoff_id = 1

    def lookup_lead(self, email: str, phone: str) -> dict | None:
        """Look up lead by email (phone not checked in mock)."""
        return self._leads.get(email.lower())

    def create_lead(self, identity: dict) -> int:
        """Create a new lead record."""
        lead_id = self._next_lead_id
        self._next_lead_id += 1

        record = {
            "lead_id": lead_id,
            "email": identity["email"],
            "mobile_phone": identity.get("phone"),
            "pin_code": None,
            "first_name": None,
            "last_name": None,
            "address_line1": None,
            "city": None,
            "state": None,
            "zip_code": None,
            "date_of_birth": None,
            "gender": None,
            "has_smartphone": None,
            "advertisement_source": None,
            "closest_rrc_site": None,
            "nicotine_products_used": None,
            "pregnant_or_nursing_or_planning": None,
            "height_feet": None,
            "height_inches": None,
            "weight_lbs": None,
            "alcohol_frequency": None,
            "alcohol_quantity": None,
            "willing_urine_drug_screen": None,
            "serious_medical_conditions": None,
            "medications_last_30_days": None,
        }
        self._leads[identity["email"].lower()] = record
        return lead_id

    def update_lead(self, lead_id: int, data: dict) -> None:
        """Update lead fields."""
        for record in self._leads.values():
            if record["lead_id"] == lead_id:
                record.update(data)
                return

    def create_handoff(self, lead_id: int, handoff_type: str, payload: dict) -> int:
        """Create a handoff record."""
        handoff_id = self._next_handoff_id
        self._next_handoff_id += 1
        self._handoffs.append({
            "handoff_id": handoff_id,
            "lead_id": lead_id,
            "handoff_type": handoff_type,
            "payload": payload,
        })
        return handoff_id
