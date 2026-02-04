"""AgentState definition for the LangGraph state machine."""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    # Study config
    study_id: str
    study_config: dict

    # Conversation
    messages: list[dict]
    current_step: str
    faq_mode: bool

    # Lead data
    lead_identity: dict
    lead_record: dict | None
    lead_id: int | None
    is_new_lead: bool

    # Auth
    pin_attempts: int
    pin_verified: bool

    # Profile completion
    missing_fields: list[str]
    collected_answers: dict

    # Pre-screen
    prescreen_answers: dict
    current_prescreen_index: int

    # Outcome
    eligibility_result: str | None
    preferred_times: list[str]
    handoff_type: str | None
