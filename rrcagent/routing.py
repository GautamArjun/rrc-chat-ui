"""Routing (conditional edge) functions for the LangGraph state machine.

Each function takes an AgentState dict and returns the name of the next node.
"""

from __future__ import annotations


def route_after_consent(state: dict) -> str:
    if state["current_step"] == "consent_declined":
        return "end"
    return "identity_collection"


def route_after_identity_collection(state: dict) -> str:
    if state["current_step"] == "identity_collected":
        return "lead_lookup"
    return "identity_collection"


def route_after_lead_lookup(state: dict) -> str:
    if state["is_new_lead"]:
        return "create_lead"
    # Skip PIN auth if the lead has no PIN set
    lead_record = state.get("lead_record") or {}
    if not lead_record.get("pin_code"):
        return "profile_collection"
    return "pin_auth"


def route_after_pin_auth(state: dict) -> str:
    if state["pin_verified"]:
        return "profile_collection"
    return "auth_fail_handoff"


def route_after_profile_collection(state: dict) -> str:
    if state["missing_fields"]:
        return "profile_collection"
    return "prescreen"


def route_after_prescreen(state: dict) -> str:
    # Check if pre-screen answer triggered disqualification
    if state.get("current_step") == "prescreen_disqualified":
        return "disqualification"

    questions = state["study_config"]["pre_screen"]["questions"]
    if state["current_prescreen_index"] < len(questions):
        return "prescreen"
    return "eligibility"


def route_after_eligibility(state: dict) -> str:
    result = state["eligibility_result"]
    if result == "DISQUALIFIED":
        return "disqualification"
    # QUALIFIED and NEEDS_HUMAN both go to scheduling
    return "scheduling"
