"""Study configuration loader.

Loads study-specific JSON configuration files from disk.
Each study has a directory under studies/<study_id>/config.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


class StudyConfigError(Exception):
    """Raised when a study configuration cannot be loaded or is invalid."""


_REQUIRED_SECTIONS = ("study", "messaging", "pre_screen", "eligibility")

# Default base path: <project_root>/studies/
# On Vercel, the structure is /var/task/rrcagent/config.py, so parent.parent = /var/task
_DEFAULT_BASE_PATH = str(
    Path(__file__).resolve().parent.parent / "studies"
)


def load_study_config(
    study_id: str,
    base_path: str | None = None,
) -> dict:
    """Load a study configuration from a JSON file.

    Args:
        study_id: Directory name under the studies folder (e.g. "zyn").
        base_path: Root directory containing study folders.
                   Defaults to <project_root>/studies/.

    Returns:
        Parsed study configuration dict.

    Raises:
        StudyConfigError: If the config file is missing, invalid, or
                          lacks required sections.
    """
    if base_path is None:
        base_path = _DEFAULT_BASE_PATH

    config_path = os.path.join(base_path, study_id, "config.json")

    if not os.path.isfile(config_path):
        raise StudyConfigError(
            f"Study configuration not found: {config_path}"
        )

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise StudyConfigError(
            f"Study configuration has invalid JSON: {config_path}: {e}"
        ) from e

    # Validate required sections
    for section in _REQUIRED_SECTIONS:
        if section not in config:
            raise StudyConfigError(
                f"Study configuration missing required section '{section}': "
                f"{config_path}"
            )

    return config
