"""
BOS Hotel Property Engine — Policies
"""

from __future__ import annotations
from typing import Optional


def room_type_must_exist_policy(room_type_id: str, store) -> Optional[str]:
    """Return error message if room_type does not exist, else None."""
    if store.get_room_type(room_type_id) is None:
        return f"room_type '{room_type_id}' not found."
    return None


def room_must_exist_policy(room_id: str, store) -> Optional[str]:
    if store.get_room(room_id) is None:
        return f"room '{room_id}' not found."
    return None


def room_must_not_be_occupied_policy(room_id: str, store) -> Optional[str]:
    room = store.get_room(room_id)
    if room and room.get("status") == "OCCUPIED":
        return f"room '{room_id}' is currently OCCUPIED."
    return None


def rate_plan_must_exist_policy(rate_plan_id: str, store) -> Optional[str]:
    if store.get_rate_plan(rate_plan_id) is None:
        return f"rate_plan '{rate_plan_id}' not found."
    return None


def rate_plan_must_be_active_policy(rate_plan_id: str, store) -> Optional[str]:
    rp = store.get_rate_plan(rate_plan_id)
    if rp and not rp.get("is_active", True):
        return f"rate_plan '{rate_plan_id}' is deactivated."
    return None


def seasonal_rate_dates_must_be_valid_policy(
    from_date: str, to_date: str
) -> Optional[str]:
    if from_date >= to_date:
        return "from_date must be before to_date."
    return None
