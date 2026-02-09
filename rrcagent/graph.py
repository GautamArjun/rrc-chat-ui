"""LangGraph state machine for the RRC recruitment agent.

build_graph() returns a compiled StateGraph (for visualization and validation).
step_graph() drives the graph turn-by-turn for interactive conversation,
running nodes that don't require user input in sequence and pausing when
the agent needs a response.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from rrcagent.state import AgentState
from rrcagent.nodes import (
    greeting_node,
    consent_node,
    identity_collection_node,
    lead_lookup_node,
    create_lead_node,
    pin_auth_node,
    auth_fail_handoff_node,
    profile_collection_node,
    prescreen_node,
    eligibility_node,
    scheduling_node,
    qualified_handoff_node,
    disqualification_node,
)
from rrcagent.routing import (
    route_after_consent,
    route_after_identity_collection,
    route_after_lead_lookup,
    route_after_pin_auth,
    route_after_profile_collection,
    route_after_prescreen,
    route_after_eligibility,
)


# ---------------------------------------------------------------------------
# Node registry and transition table
# ---------------------------------------------------------------------------

# Nodes that produce an assistant message and then need user input
_WAIT_FOR_INPUT = {
    "greeting",
    "consent",
    "identity_collection",
    "pin_auth",
    "profile_collection",
    "prescreen",
    "scheduling",
}

# Terminal nodes — flow ends after these
_TERMINAL = {"end", "auth_fail_handoff", "qualified_handoff", "disqualification"}

# Maps current_step values to the next node(s) via routing
_ROUTING_TABLE = {
    "consent": route_after_consent,
    "identity_collection": route_after_identity_collection,
    "lead_lookup": route_after_lead_lookup,
    "pin_auth": route_after_pin_auth,
    "profile_collection": route_after_profile_collection,
    "prescreen": route_after_prescreen,
    "eligibility": route_after_eligibility,
}

# Direct edges (no routing needed)
_DIRECT_EDGES = {
    "greeting": "consent",
    "create_lead": "profile_collection",
    "scheduling": "qualified_handoff",
}


def _get_node_fn(node_name: str):
    """Return the node function for a given node name."""
    return {
        "greeting": greeting_node,
        "consent": consent_node,
        "identity_collection": identity_collection_node,
        "lead_lookup": lead_lookup_node,
        "create_lead": create_lead_node,
        "pin_auth": pin_auth_node,
        "auth_fail_handoff": auth_fail_handoff_node,
        "profile_collection": profile_collection_node,
        "prescreen": prescreen_node,
        "eligibility": eligibility_node,
        "scheduling": scheduling_node,
        "qualified_handoff": qualified_handoff_node,
        "disqualification": disqualification_node,
    }[node_name]


def _next_node(node_name: str, state: dict) -> str | None:
    """Determine the next node given the current node and state."""
    if node_name in _TERMINAL:
        return None
    if node_name in _DIRECT_EDGES:
        return _DIRECT_EDGES[node_name]
    if node_name in _ROUTING_TABLE:
        return _ROUTING_TABLE[node_name](state)
    return None


def _merge(state: dict, update: dict) -> dict:
    """Merge a node's output into the current state."""
    if not update:
        return state
    return {**state, **update}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_graph(services: dict | None = None) -> StateGraph:
    """Build and compile the LangGraph StateGraph.

    This is useful for visualization and schema validation.
    For interactive stepping, use step_graph() instead.
    """
    def _wrap(fn):
        def wrapper(state: dict) -> dict:
            return fn(state, services=services)
        wrapper.__name__ = fn.__name__
        return wrapper

    builder = StateGraph(AgentState)

    builder.add_node("greeting", greeting_node)
    builder.add_node("consent", consent_node)
    builder.add_node("identity_collection", identity_collection_node)
    builder.add_node("lead_lookup", _wrap(lead_lookup_node))
    builder.add_node("create_lead", _wrap(create_lead_node))
    builder.add_node("pin_auth", pin_auth_node)
    builder.add_node("auth_fail_handoff", _wrap(auth_fail_handoff_node))
    builder.add_node("profile_collection", _wrap(profile_collection_node))
    builder.add_node("prescreen", prescreen_node)
    builder.add_node("eligibility", eligibility_node)
    builder.add_node("scheduling", scheduling_node)
    builder.add_node("qualified_handoff", _wrap(qualified_handoff_node))
    builder.add_node("disqualification", disqualification_node)
    builder.add_node("end", lambda state: state)

    builder.add_edge(START, "greeting")
    builder.add_edge("greeting", "consent")
    builder.add_conditional_edges("consent", route_after_consent)
    builder.add_conditional_edges("identity_collection", route_after_identity_collection)
    builder.add_conditional_edges("lead_lookup", route_after_lead_lookup)
    builder.add_edge("create_lead", "profile_collection")
    builder.add_conditional_edges("pin_auth", route_after_pin_auth)
    builder.add_edge("auth_fail_handoff", END)
    builder.add_conditional_edges("profile_collection", route_after_profile_collection)
    builder.add_conditional_edges("prescreen", route_after_prescreen)
    builder.add_conditional_edges("eligibility", route_after_eligibility)
    builder.add_edge("scheduling", "qualified_handoff")
    builder.add_edge("qualified_handoff", END)
    builder.add_edge("disqualification", END)
    builder.add_edge("end", END)

    return builder.compile()


def _default_state(study_id: str, study_config: dict) -> dict:
    """Create a fresh initial state."""
    return {
        "study_id": study_id,
        "study_config": study_config,
        "messages": [],
        "current_step": "",
        "faq_mode": False,
        "lead_identity": {},
        "lead_record": None,
        "lead_id": None,
        "is_new_lead": False,
        "pin_attempts": 0,
        "pin_verified": False,
        "missing_fields": [],
        "collected_answers": {},
        "prescreen_answers": {},
        "current_prescreen_index": 0,
        "eligibility_result": None,
        "preferred_times": [],
        "handoff_type": None,
    }


def step_graph(
    graph,
    *,
    state: dict | None = None,
    study_id: str | None = None,
    study_config: dict | None = None,
    user_message: str | None = None,
    services: dict | None = None,
) -> dict:
    """Step through the conversation one turn at a time.

    On first call: provide study_id and study_config. Runs greeting node,
    returns state with greeting message (waiting for user consent).

    On subsequent calls: provide state and user_message. Runs the current
    node with the user's input, then continues running any nodes that don't
    need user input (e.g., lead_lookup, eligibility) until it hits a node
    that needs input or a terminal node.
    """
    if state is None:
        # Initialize
        state = _default_state(study_id, study_config)
        # Run greeting node
        result = greeting_node(state)
        state = _merge(state, result)
        return state

    # Add user message
    if user_message is not None:
        state = {
            **state,
            "messages": state["messages"] + [
                {"role": "user", "content": user_message}
            ],
        }

    # Determine which node to run based on current_step
    current = _resolve_current_node(state)
    if current is None:
        return state

    # Run the current node (processes the user's message)
    node_fn = _get_node_fn(current)
    result = node_fn(state, services=services) if services else node_fn(state)
    state = _merge(state, result)

    # After running, determine next node and keep going until we need input
    next_node = _next_node(current, state)
    while next_node and next_node not in _WAIT_FOR_INPUT and next_node != "end":
        node_fn = _get_node_fn(next_node)
        result = node_fn(state, services=services) if services else node_fn(state)
        state = _merge(state, result)

        if next_node in _TERMINAL:
            break

        prev = next_node
        next_node = _next_node(prev, state)

    # If we landed on a wait-for-input node that hasn't been run yet
    # (e.g., after lead_lookup -> profile_collection), run it to produce
    # the prompt message
    if next_node and next_node in _WAIT_FOR_INPUT and next_node != current:
        node_fn = _get_node_fn(next_node)
        result = node_fn(state, services=services) if services else node_fn(state)
        state = _merge(state, result)

        # Check if the node completed without needing input (e.g.,
        # profile_collection with no missing fields sets profile_complete).
        # If _resolve_current_node returns a different node, the wait-for-input
        # node finished instantly and we should keep advancing.
        resolved = _resolve_current_node(state)
        if resolved is not None and resolved != next_node:
            # Continue auto-advancing through non-interactive nodes
            follow = _next_node(next_node, state)
            while follow and follow not in _WAIT_FOR_INPUT and follow != "end":
                node_fn = _get_node_fn(follow)
                result = node_fn(state, services=services) if services else node_fn(state)
                state = _merge(state, result)
                if follow in _TERMINAL:
                    break
                follow = _next_node(follow, state)

            # Run the next wait-for-input node if we reached one
            if follow and follow in _WAIT_FOR_INPUT:
                node_fn = _get_node_fn(follow)
                result = node_fn(state, services=services) if services else node_fn(state)
                state = _merge(state, result)

    return state


def _resolve_current_node(state: dict) -> str | None:
    """Map current_step to the node that should process the user's input."""
    step = state.get("current_step", "")

    if step == "greeting":
        return "consent"
    if step == "awaiting_consent":
        return "consent"
    if step == "consent_given":
        return "identity_collection"
    if step == "consent_declined":
        return None  # terminal
    if step in ("identity_collected", "collecting_identity"):
        return "identity_collection"
    if step in ("lead_found", "lead_not_found"):
        return None  # shouldn't be called with user input here
    if step == "lead_created":
        return "profile_collection"
    if step == "awaiting_pin":
        return "pin_auth"
    if step == "pin_verified":
        return "profile_collection"
    if step == "pin_failed":
        return None  # terminal (auth fail handoff already ran)
    if step.startswith("collecting_group:") or step.startswith("collecting:"):
        return "profile_collection"
    if step == "profile_complete":
        return "prescreen"
    if step.startswith("prescreen:"):
        return "prescreen"
    if step == "prescreen_complete":
        return "eligibility"
    if step == "prescreen_disqualified":
        return None  # routing sends to disqualification
    if step.startswith("eligibility_"):
        return None  # routing already happened
    if step == "scheduling":
        return "scheduling"
    if step == "scheduling_complete":
        return "qualified_handoff"
    if step in ("auth_fail_handoff", "qualified_handoff", "disqualified"):
        return None  # terminal

    return None
