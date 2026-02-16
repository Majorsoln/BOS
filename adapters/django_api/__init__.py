"""
BOS Django HTTP adapter.
Thin framework glue over core/http_api handlers.
"""

from adapters.django_api.wiring import (
    DEV_ADMIN_API_KEY,
    DEV_ADMIN_BRANCH_ID,
    DEV_BUSINESS_ID,
    DEV_CASHIER_API_KEY,
    DEV_CASHIER_BRANCH_ID,
    build_dependencies,
)

__all__ = [
    "DEV_ADMIN_API_KEY",
    "DEV_CASHIER_API_KEY",
    "DEV_BUSINESS_ID",
    "DEV_ADMIN_BRANCH_ID",
    "DEV_CASHIER_BRANCH_ID",
    "build_dependencies",
]

