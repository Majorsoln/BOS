"""
BOS BI Projections — KPI Store
================================
Thread-safe in-memory store for business KPI counters.

Counters are keyed by (business_id, kpi_key) and accumulate
integer or float values as events are dispatched.

This store is rebuilt from events on system restart via the
replay engine — it is NOT persisted to the database.

Usage:
    from projections.bi.kpi_store import increment, get_kpis, get_kpi

    increment("biz-uuid", "QUOTES_GENERATED", 1)
    increment("biz-uuid", "QUOTE_VALUE", 5000)
    get_kpis("biz-uuid")  # {"QUOTES_GENERATED": 1, "QUOTE_VALUE": 5000}
"""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Union

_KPI_DATA: dict[str, dict[str, Union[int, float]]] = defaultdict(dict)
_LOCK = Lock()


def increment(
    business_id: str,
    kpi_key: str,
    amount: Union[int, float] = 1,
) -> None:
    """Add amount to the KPI counter for (business_id, kpi_key)."""
    with _LOCK:
        current = _KPI_DATA[business_id].get(kpi_key, 0)
        _KPI_DATA[business_id][kpi_key] = current + amount


def get_kpis(business_id: str) -> dict[str, Union[int, float]]:
    """Return a snapshot of all KPIs for a business."""
    with _LOCK:
        return dict(_KPI_DATA.get(business_id, {}))


def get_kpi(
    business_id: str,
    kpi_key: str,
    default: Union[int, float] = 0,
) -> Union[int, float]:
    """Return a single KPI value for a business, or default if not set."""
    with _LOCK:
        return _KPI_DATA.get(business_id, {}).get(kpi_key, default)


def reset(business_id: str | None = None) -> None:
    """
    Reset KPI data.

    If business_id is provided, reset only that business.
    If None, reset all businesses (useful for testing).
    """
    with _LOCK:
        if business_id is None:
            _KPI_DATA.clear()
        else:
            _KPI_DATA.pop(business_id, None)
