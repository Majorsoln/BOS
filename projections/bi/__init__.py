"""
BOS BI Projections — Read-Side Analytics
=========================================
The BI/reporting projection store lives in:
    engines/reporting/services.ReportingProjectionStore

This module is the canonical import point for BI projections in
read-side consumers (dashboards, APIs, exports).

Usage:
    from engines.reporting.services import ReportingProjectionStore
    store = ReportingProjectionStore()
    store.get_kpi_series("REVENUE_TOTAL")
    store.sum_kpi("REVENUE_TOTAL")
    store.latest_kpi_value("HOURS_WORKED")
"""
