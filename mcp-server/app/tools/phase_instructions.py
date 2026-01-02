"""
AI Personality Instructions by Phase

Edit these strings to change how the AI behaves at each progression phase.
Simple rule: fetch_preferences checks phase, returns matching instructions.

PHASES:
- beginner: New users, no data yet
- student: First statement saved, learning categorization
- analyst: First budget set, tracking spending
- advisor: 6+ months of data, optimization mode
- master: 12+ months, strategic planning
"""

from app.prompts import load_prompt

# ============================================================================
# PHASE 1: BEGINNER (Default - no data yet)
# ============================================================================
BEGINNER_INSTRUCTIONS = load_prompt("phases/beginner.txt").strip()

# ============================================================================
# PHASE 2: STUDENT (First statement saved)
# ============================================================================
STUDENT_INSTRUCTIONS = load_prompt("phases/student.txt").strip()

# ============================================================================
# PHASE 3: ANALYST (First budget set)
# ============================================================================
ANALYST_INSTRUCTIONS = load_prompt("phases/analyst.txt").strip()

# ============================================================================
# PHASE 4: ADVISOR (6+ months of data)
# ============================================================================
ADVISOR_INSTRUCTIONS = load_prompt("phases/advisor.txt").strip()

# ============================================================================
# PHASE 5: MASTER (12+ months of data)
# ============================================================================
MASTER_INSTRUCTIONS = load_prompt("phases/master.txt").strip()

# ============================================================================
# PHASE MAPPING
# ============================================================================

# Map phase names to instructions (used by fetch_preferences)
PHASE_INSTRUCTIONS = {
    "beginner": BEGINNER_INSTRUCTIONS,
    "student": STUDENT_INSTRUCTIONS,
    "analyst": ANALYST_INSTRUCTIONS,
    "advisor": ADVISOR_INSTRUCTIONS,
    "master": MASTER_INSTRUCTIONS,
}

# Phase trigger definitions (milestone IDs that unlock each phase)
# These are checked in order from master -> beginner (most advanced first)
PHASE_TRIGGERS = {
    "beginner": None,  # Default state
    "student": "month_1",  # First statement saved
    "analyst": "first_budget",  # First budget created
    "advisor": "month_6",  # 6 months of data
    "master": "month_12",  # 12 months of data
}

# Phase display names and mascot variants
PHASE_METADATA = {
    "beginner": {
        "display_name": "Beginner",
        "mascot": "base",
        "description": "Learning the basics",
    },
    "student": {
        "display_name": "Student",
        "mascot": "teacher",
        "description": "Building good habits",
    },
    "analyst": {
        "display_name": "Analyst",
        "mascot": "analyst",
        "description": "Tracking patterns",
    },
    "advisor": {
        "display_name": "Advisor",
        "mascot": "presenter",
        "description": "Optimizing finances",
    },
    "master": {
        "display_name": "Master",
        "mascot": "wallet",
        "description": "Financial mastery",
    },
}


def determine_user_phase(total_months: int = 0, budgets_configured: int = 0) -> str:
    """
    Determine user's current phase based on their data.
    
    Simple if/then logic - check from most advanced to least advanced.
    
    Args:
        total_months: Number of months of saved data
        budgets_configured: Number of budgets the user has set
    
    Returns:
        Phase name string: "beginner", "student", "analyst", "advisor", or "master"
    """
    if total_months >= 12:
        return "master"
    if total_months >= 6:
        return "advisor"
    if budgets_configured >= 1:
        return "analyst"
    if total_months >= 1:
        return "student"
    return "beginner"


def get_phase_instructions(phase: str) -> str:
    """Get AI instructions for a given phase."""
    return PHASE_INSTRUCTIONS.get(phase, BEGINNER_INSTRUCTIONS)


def get_phase_metadata(phase: str) -> dict:
    """Get display metadata for a given phase."""
    return PHASE_METADATA.get(phase, PHASE_METADATA["beginner"])
