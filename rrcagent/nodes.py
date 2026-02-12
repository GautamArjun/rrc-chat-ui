"""Node functions for the LangGraph state machine.

Each node takes AgentState (and optionally a services dict for DB access)
and returns a partial state dict to be merged by LangGraph.
"""

from __future__ import annotations

import json
import re

from rrcagent.eligibility import evaluate as evaluate_eligibility


# ---------------------------------------------------------------------------
# Required profile fields (demographics + health)
# ---------------------------------------------------------------------------

REQUIRED_PROFILE_FIELDS = [
    "first_name",
    "last_name",
    "address_line1",
    "city",
    "state",
    "zip_code",
    "date_of_birth",
    "gender",
    "has_smartphone",
    "advertisement_source",
    "closest_rrc_site",
    "nicotine_products_used",
    "pregnant_or_nursing_or_planning",
    "height_feet",
    "height_inches",
    "weight_lbs",
    "alcohol_frequency",
    "alcohol_quantity",
    "willing_urine_drug_screen",
    "serious_medical_conditions",
    "medications_last_30_days",
]


PROFILE_FIELD_GROUPS = [
    {
        "name": "personal",
        "label": "Personal Information",
        "fields": ["first_name", "last_name", "date_of_birth", "gender"],
    },
    {
        "name": "address",
        "label": "Address",
        "fields": ["address_line1", "city", "state", "zip_code"],
    },
    {
        "name": "study",
        "label": "Study Details",
        "fields": [
            "has_smartphone", "advertisement_source",
            "closest_rrc_site", "nicotine_products_used",
        ],
    },
    {
        "name": "health",
        "label": "Health & Lifestyle",
        "fields": [
            "pregnant_or_nursing_or_planning",
            "height_feet", "height_inches", "weight_lbs",
            "alcohol_frequency", "alcohol_quantity",
            "willing_urine_drug_screen",
            "serious_medical_conditions", "medications_last_30_days",
        ],
    },
]


# ---------------------------------------------------------------------------
# Prescreen question ID → lead record column name
# (only stable numeric fields with clear 1:1 DB column mappings)
# ---------------------------------------------------------------------------

PRESCREEN_TO_LEAD_FIELD = {
    "cigarettes_per_day": "cigarettes_per_day",
    "cigarette_days_per_week": "cigarette_days_per_week",
    "cigarette_years": "cigarette_years_smoked",
}


def _next_group_for_missing(missing: list[str]) -> dict | None:
    """Find the first group that has any missing fields."""
    missing_set = set(missing)
    for group in PROFILE_FIELD_GROUPS:
        group_missing = [f for f in group["fields"] if f in missing_set]
        if group_missing:
            return group
    return None


def _msg(role: str, content: str) -> dict:
    return {"role": role, "content": content}


def _last_user_text(state: dict) -> str:
    """Extract text of the last user message."""
    for msg in reversed(state.get("messages", [])):
        if msg["role"] == "user":
            return msg["content"]
    return ""


def _compute_missing_fields(lead_record: dict | None) -> list[str]:
    """Determine which required profile fields are missing from a lead record."""
    if lead_record is None:
        return list(REQUIRED_PROFILE_FIELDS)
    return [
        f for f in REQUIRED_PROFILE_FIELDS
        if lead_record.get(f) is None
    ]


# ---------------------------------------------------------------------------
# Greeting
# ---------------------------------------------------------------------------

def greeting_node(state: dict, **kwargs) -> dict:
    greeting_text = state["study_config"]["messaging"]["greeting"]
    consent_prompt = " Would you like to learn more and see if you qualify?"
    return {
        "messages": state["messages"] + [_msg("assistant", greeting_text + consent_prompt)],
        "current_step": "greeting",
    }


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------

_CONSENT_YES_PATTERNS = re.compile(
    r"\b(yes|yeah|yep|sure|ok|okay|proceed|continue|let'?s go|i'?d like)\b",
    re.IGNORECASE,
)

_CONSENT_NO_PATTERNS = re.compile(
    r"\b(no|nah|nope|not interested|decline|stop|don'?t)\b",
    re.IGNORECASE,
)


def consent_node(state: dict, **kwargs) -> dict:
    user_text = _last_user_text(state)
    if _CONSENT_YES_PATTERNS.search(user_text):
        return {
            "messages": state["messages"] + [
                _msg("assistant", "Great! Let's get started. Could you please provide your email address and phone number?")
            ],
            "current_step": "consent_given",
        }
    if _CONSENT_NO_PATTERNS.search(user_text):
        return {
            "messages": state["messages"] + [
                _msg("assistant", "No problem at all. Thank you for your time and take care!")
            ],
            "current_step": "consent_declined",
        }
    # Ambiguous — re-prompt
    return {
        "messages": state["messages"] + [
            _msg("assistant", "Would you like to proceed and see if you qualify for the study? Just say yes or no.")
        ],
        "current_step": "awaiting_consent",
    }


# ---------------------------------------------------------------------------
# Identity Collection
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\d{10}")


def identity_collection_node(state: dict, **kwargs) -> dict:
    user_text = _last_user_text(state)

    # Try JSON first (form submission from frontend)
    parsed = _try_parse_json(user_text)
    if parsed and "email" in parsed and "phone" in parsed:
        email = parsed["email"].strip()
        phone = "".join(c for c in parsed["phone"] if c.isdigit())
        if _EMAIL_RE.match(email) and len(phone) >= 10:
            return {
                "lead_identity": {"email": email, "phone": phone[:10]},
                "current_step": "identity_collected",
                "messages": state["messages"] + [
                    _msg("assistant", "Thank you! Let me look up your information.")
                ],
            }

    # Fallback: regex extraction from plain text
    email_match = _EMAIL_RE.search(user_text)
    phone_match = _PHONE_RE.search(user_text.replace("-", "").replace(" ", "").replace("(", "").replace(")", ""))

    if email_match and phone_match:
        return {
            "lead_identity": {
                "email": email_match.group(),
                "phone": phone_match.group(),
            },
            "current_step": "identity_collected",
            "messages": state["messages"] + [
                _msg("assistant", "Thank you! Let me look up your information.")
            ],
        }

    # Ask for what's missing
    return {
        "messages": state["messages"] + [
            _msg("assistant", "Could you please provide your email address and phone number so I can look up your information?")
        ],
        "current_step": "collecting_identity",
    }


# ---------------------------------------------------------------------------
# Lead Lookup
# ---------------------------------------------------------------------------

def lead_lookup_node(state: dict, services: dict | None = None, **kwargs) -> dict:
    db = services["db"]
    identity = state["lead_identity"]
    record = db.lookup_lead(identity["email"], identity["phone"])
    if record is not None:
        return {
            "is_new_lead": False,
            "lead_record": record,
            "lead_id": record["lead_id"],
            "missing_fields": _compute_missing_fields(record),
            "current_step": "lead_found",
        }
    return {
        "is_new_lead": True,
        "lead_record": None,
        "lead_id": None,
        "current_step": "lead_not_found",
    }


# ---------------------------------------------------------------------------
# Create Lead
# ---------------------------------------------------------------------------

def create_lead_node(state: dict, services: dict | None = None, **kwargs) -> dict:
    db = services["db"]
    identity = state["lead_identity"]
    lead_id = db.create_lead(identity)
    return {
        "lead_id": lead_id,
        "is_new_lead": True,
        "missing_fields": list(REQUIRED_PROFILE_FIELDS),
        "current_step": "lead_created",
    }


# ---------------------------------------------------------------------------
# PIN Auth
# ---------------------------------------------------------------------------

def pin_auth_node(state: dict, **kwargs) -> dict:
    current_step = state.get("current_step", "")

    # First entry — ask for PIN
    if current_step != "awaiting_pin":
        return {
            "current_step": "awaiting_pin",
            "messages": state["messages"] + [
                _msg("assistant", "I found your record. For security, please enter your PIN to verify your identity.")
            ],
        }

    # Validate PIN
    user_text = _last_user_text(state).strip()
    expected_pin = state["lead_record"]["pin_code"]
    attempts = state.get("pin_attempts", 0) + 1

    if user_text == expected_pin:
        return {
            "pin_verified": True,
            "pin_attempts": attempts,
            "handoff_type": None,
            "current_step": "pin_verified",
            "messages": state["messages"] + [
                _msg("assistant", "Identity confirmed. Let me continue with your profile.")
            ],
        }
    return {
        "pin_verified": False,
        "pin_attempts": attempts,
        "handoff_type": "AUTH_FAIL",
        "current_step": "pin_failed",
    }


# ---------------------------------------------------------------------------
# Auth Fail Handoff
# ---------------------------------------------------------------------------

def auth_fail_handoff_node(state: dict, services: dict | None = None, **kwargs) -> dict:
    db = services["db"]
    lead_id = state["lead_id"]
    db.create_handoff(lead_id, "AUTH_FAIL", {"reason": "PIN verification failed"})
    failure_msg = state["study_config"]["messaging"]["pin_failure"]
    return {
        "messages": state["messages"] + [_msg("assistant", failure_msg)],
        "current_step": "auth_fail_handoff",
    }


# ---------------------------------------------------------------------------
# Profile Collection
# ---------------------------------------------------------------------------

_FIELD_PROMPTS = {
    "first_name": "What is your first name?",
    "last_name": "What is your last name?",
    "address_line1": "What is your street address?",
    "city": "What city do you live in?",
    "state": "What state do you live in?",
    "zip_code": "What is your ZIP code?",
    "date_of_birth": "What is your date of birth?",
    "gender": "What is your gender?",
    "has_smartphone": "Do you have a smartphone with texting and data capability?",
    "advertisement_source": "How did you hear about this study?",
    "closest_rrc_site": "Which RRC site is closest to you: Raleigh or Charlotte?",
    "nicotine_products_used": "What nicotine products do you use?",
    "pregnant_or_nursing_or_planning": "Are you pregnant, nursing, or planning to become pregnant?",
    "height_feet": "How tall are you (feet)?",
    "height_inches": "And how many inches?",
    "weight_lbs": "What is your weight in pounds?",
    "alcohol_frequency": "How often do you drink alcohol?",
    "alcohol_quantity": "When you drink, how many drinks do you typically have?",
    "willing_urine_drug_screen": "Are you willing to submit to a urine drug screen?",
    "serious_medical_conditions": "Do you have any current or past serious medical or psychiatric conditions?",
    "medications_last_30_days": "Please list any prescriptions, OTC medications, or supplements taken in the last 30 days.",
}


def _try_parse_json(text: str) -> dict | None:
    """Try to parse text as JSON. Returns dict or None."""
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _prompt_for_group(group: dict, missing: list[str]) -> str:
    """Build a prompt message for a field group."""
    group_missing = [f for f in group["fields"] if f in set(missing)]
    if not group_missing:
        return ""
    return f"Please fill in your {group['label'].lower()}."


def _advance_to_next_group(missing: list[str], state: dict) -> dict:
    """Determine the next group step and prompt, or mark profile complete."""
    if not missing:
        return {
            "missing_fields": [],
            "current_step": "profile_complete",
        }

    group = _next_group_for_missing(missing)
    if group:
        prompt = _prompt_for_group(group, missing)
        return {
            "missing_fields": missing,
            "current_step": f"collecting_group:{group['name']}",
            "messages": state["messages"] + [_msg("assistant", prompt)],
        }

    # Fallback: single field mode for any ungrouped fields
    next_field = missing[0]
    prompt = _FIELD_PROMPTS.get(next_field, f"Please provide your {next_field}.")
    return {
        "missing_fields": missing,
        "current_step": f"collecting:{next_field}",
        "messages": state["messages"] + [_msg("assistant", prompt)],
    }


def profile_collection_node(state: dict, services: dict | None = None, **kwargs) -> dict:
    missing = list(state["missing_fields"])
    current_step = state.get("current_step", "")

    # Batch JSON submission (from grouped form)
    if current_step.startswith("collecting_group:") or current_step.startswith("collecting:"):
        user_text = _last_user_text(state)
        batch = _try_parse_json(user_text)

        if batch:
            # Process all fields in the batch
            new_collected = {**state.get("collected_answers", {})}
            for field_name, answer in batch.items():
                new_collected[field_name] = str(answer).strip()
                missing = [f for f in missing if f != field_name]
                if services:
                    db = services["db"]
                    db.update_lead(state["lead_id"], {field_name: str(answer).strip()})

            result = _advance_to_next_group(missing, state)
            result["collected_answers"] = new_collected
            return result

        # Single field answer (backward compatible)
        if current_step.startswith("collecting:"):
            field_name = current_step.split(":", 1)[1]
            answer = user_text.strip()
            new_collected = {**state.get("collected_answers", {}), field_name: answer}
            missing = [f for f in missing if f != field_name]

            if services:
                db = services["db"]
                db.update_lead(state["lead_id"], {field_name: answer})

            result = _advance_to_next_group(missing, state)
            result["collected_answers"] = new_collected
            return result

    # First entry — start with the first group
    if missing:
        return _advance_to_next_group(missing, state)

    return {"current_step": "profile_complete", "missing_fields": []}


# ---------------------------------------------------------------------------
# Pre-Screen
# ---------------------------------------------------------------------------

def _find_question_by_id(questions: list[dict], q_id: str) -> dict | None:
    """Find a question by its ID."""
    for q in questions:
        if q["id"] == q_id:
            return q
    return None


def _check_disqualify_on(question: dict, answer: str) -> bool:
    """Check if the answer triggers disqualification for this question.

    Args:
        question: The question config dict.
        answer: The user's answer (lowercased).

    Returns:
        True if the answer should disqualify, False otherwise.
    """
    disqualify_on = question.get("disqualify_on")
    if disqualify_on is None:
        return False

    # Normalize for comparison
    disqualify_on = str(disqualify_on).lower()
    answer = answer.strip().lower()

    # Handle yes/no answers
    if disqualify_on == "yes":
        return answer in ("yes", "y", "true", "1")
    if disqualify_on == "no":
        return answer in ("no", "n", "false", "0")

    # Exact match for other values
    return answer == disqualify_on


def _advance_past_answered(questions, start_index, lead_record, prescreen_answers):
    """Skip prescreen questions whose answer already exists in the lead record.

    Auto-fills prescreen_answers for skipped questions and returns
    (next_index, updated_answers) where next_index is the first question
    that still needs asking, or len(questions) if all are answered.
    """
    answers = dict(prescreen_answers)
    idx = start_index
    while idx < len(questions):
        q = questions[idx]
        lead_field = PRESCREEN_TO_LEAD_FIELD.get(q["id"])
        if lead_field and lead_record and lead_record.get(lead_field) is not None:
            # Auto-fill from lead record
            answers[q["id"]] = str(lead_record[lead_field])
            idx += 1
            continue
        break
    return idx, answers


def prescreen_node(state: dict, services: dict | None = None, **kwargs) -> dict:
    questions = state["study_config"]["pre_screen"]["questions"]
    index = state["current_prescreen_index"]
    current_step = state.get("current_step", "")
    lead_record = state.get("lead_record") or {}

    # If we're collecting an answer to a prescreen question
    if current_step.startswith("prescreen:"):
        q_id = current_step.split(":", 1)[1]
        user_text = _last_user_text(state).strip().lower()
        new_answers = {**state.get("prescreen_answers", {}), q_id: user_text}
        new_index = index + 1

        # Persist mapped prescreen fields to lead record
        lead_field = PRESCREEN_TO_LEAD_FIELD.get(q_id)
        if lead_field and services and state.get("lead_id"):
            try:
                services["db"].update_lead(state["lead_id"], {lead_field: user_text})
            except Exception:
                pass  # Non-critical; answers are still in session state

        # Check if this answer triggers disqualification
        current_question = _find_question_by_id(questions, q_id)
        if current_question and _check_disqualify_on(current_question, user_text):
            return {
                "prescreen_answers": new_answers,
                "current_prescreen_index": new_index,
                "current_step": "prescreen_disqualified",
            }

        # Skip past questions already answered in lead record
        new_index, new_answers = _advance_past_answered(
            questions, new_index, lead_record, new_answers,
        )

        if new_index >= len(questions):
            return {
                "prescreen_answers": new_answers,
                "current_prescreen_index": new_index,
                "current_step": "prescreen_complete",
            }

        # Ask next question
        next_q = questions[new_index]
        return {
            "prescreen_answers": new_answers,
            "current_prescreen_index": new_index,
            "current_step": f"prescreen:{next_q['id']}",
            "messages": state["messages"] + [_msg("assistant", next_q["question"])],
        }

    # First entry — skip past any already-answered questions
    index, filled_answers = _advance_past_answered(
        questions, index, lead_record, state.get("prescreen_answers", {}),
    )

    if index >= len(questions):
        return {
            "prescreen_answers": filled_answers,
            "current_prescreen_index": index,
            "current_step": "prescreen_complete",
        }

    q = questions[index]
    return {
        "prescreen_answers": filled_answers,
        "current_prescreen_index": index,
        "current_step": f"prescreen:{q['id']}",
        "messages": state["messages"] + [_msg("assistant", q["question"])],
    }


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------

def _coerce_prescreen_value(value: str):
    """Coerce a prescreen answer string to int, float, or bool if possible."""
    if value.lower() in ("yes", "true"):
        return True
    if value.lower() in ("no", "false"):
        return False
    try:
        return int(value)
    except (ValueError, TypeError):
        pass
    try:
        return float(value)
    except (ValueError, TypeError):
        pass
    return value


def eligibility_node(state: dict, **kwargs) -> dict:
    # Build profile from lead_record + collected_answers
    profile = {}
    if state.get("lead_record"):
        profile.update(state["lead_record"])
    if state.get("collected_answers"):
        profile.update(state["collected_answers"])

    # Merge prescreen answers (only for fields not already present)
    for q_id, raw_value in (state.get("prescreen_answers") or {}).items():
        lead_field = PRESCREEN_TO_LEAD_FIELD.get(q_id, q_id)
        if lead_field not in profile or profile[lead_field] is None:
            profile[lead_field] = _coerce_prescreen_value(raw_value)

    # Calculate age from date_of_birth if present
    if "date_of_birth" in profile and profile["date_of_birth"] and "age" not in profile:
        from datetime import date

        dob = profile["date_of_birth"]
        if isinstance(dob, str):
            parts = dob.split("-")
            dob = date(int(parts[0]), int(parts[1]), int(parts[2]))
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        profile["age"] = age

    rules = state["study_config"]["eligibility"]
    outcome, reasons = evaluate_eligibility(profile, rules)

    return {
        "eligibility_result": outcome,
        "current_step": f"eligibility_{outcome.lower()}",
    }


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

def scheduling_node(state: dict, **kwargs) -> dict:
    current_step = state.get("current_step", "")

    if current_step == "scheduling":
        user_text = _last_user_text(state).strip()
        parsed = _try_parse_json(user_text)

        if parsed and "preferred_days" in parsed and "preferred_times" in parsed:
            days = parsed["preferred_days"]
            time_slots = parsed["preferred_times"]
            combined = [f"{day} {slot}" for day in days for slot in time_slots]
            return {
                "preferred_times": combined,
                "current_step": "scheduling_complete",
            }

        # Fallback: comma-separated plain text
        times = [t.strip() for t in user_text.split(",") if t.strip()] or [user_text]
        return {
            "preferred_times": times,
            "current_step": "scheduling_complete",
        }

    return {
        "current_step": "scheduling",
        "messages": state["messages"] + [
            _msg(
                "assistant",
                "You may be eligible for this study! When would be a good time for a screening call? "
                "Please select your preferred days and times.",
            )
        ],
    }


# ---------------------------------------------------------------------------
# Qualified Handoff
# ---------------------------------------------------------------------------

def qualified_handoff_node(state: dict, services: dict | None = None, **kwargs) -> dict:
    db = services["db"]
    lead_id = state["lead_id"]
    db.create_handoff(lead_id, "QUALIFIED", {
        "preferred_times": state.get("preferred_times", []),
    })
    return {
        "current_step": "qualified_handoff",
        "messages": state["messages"] + [
            _msg(
                "assistant",
                "Thank you! A member of our team will reach out to schedule your screening call.",
            )
        ],
    }


# ---------------------------------------------------------------------------
# Disqualification
# ---------------------------------------------------------------------------

def disqualification_node(state: dict, **kwargs) -> dict:
    msg_text = state["study_config"]["messaging"]["disqualification"]
    return {
        "current_step": "disqualified",
        "messages": state["messages"] + [_msg("assistant", msg_text)],
    }
