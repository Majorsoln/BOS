"""
BOS Hotel Reservation Engine — Policies
"""
from __future__ import annotations
from typing import Optional


def reservation_must_exist_policy(reservation_id: str, store) -> Optional[str]:
    if store.get_reservation(reservation_id) is None:
        return f"reservation '{reservation_id}' not found."
    return None


def reservation_must_be_status_policy(
    reservation_id: str, expected: str, store
) -> Optional[str]:
    res = store.get_reservation(reservation_id)
    if res and res.get("status") != expected:
        return (f"reservation '{reservation_id}' is {res.get('status')} "
                f"— expected {expected}.")
    return None


def reservation_must_not_be_terminal_policy(
    reservation_id: str, store
) -> Optional[str]:
    terminal = {"CANCELLED", "NO_SHOW", "CHECKED_OUT"}
    res = store.get_reservation(reservation_id)
    if res and res.get("status") in terminal:
        return (f"reservation '{reservation_id}' is already "
                f"{res.get('status')} (terminal state).")
    return None


def room_must_be_available_policy(room_id: str, store) -> Optional[str]:
    """Check property store for room availability."""
    room = store.get_room(room_id)
    if room is None:
        return f"room '{room_id}' not found."
    if room.get("status") != "AVAILABLE":
        return f"room '{room_id}' is {room.get('status')} — not available."
    return None


def no_show_must_not_exceed_charge_policy(
    no_show_charge: int, total_amount: int
) -> Optional[str]:
    if no_show_charge > total_amount:
        return "no_show_charge cannot exceed reservation total_amount."
    return None
