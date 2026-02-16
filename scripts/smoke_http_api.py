"""
Manual smoke runner for BOS Django adapter endpoints.

Usage:
    python scripts/smoke_http_api.py
    python scripts/smoke_http_api.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
from urllib import error, request


DEV_ADMIN_API_KEY = "dev-admin-key"
DEV_CASHIER_API_KEY = "dev-cashier-key"
DEV_BUSINESS_ID = "11111111-1111-1111-1111-111111111111"
DEV_ADMIN_BRANCH_ID = "22222222-2222-2222-2222-222222222222"
DEV_CASHIER_BRANCH_ID = "33333333-3333-3333-3333-333333333333"


def _call(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict | None = None,
) -> tuple[int, dict]:
    encoded = None
    req_headers = dict(headers)
    if body is not None:
        encoded = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = request.Request(url=url, method=method, headers=req_headers, data=encoded)
    try:
        with request.urlopen(req) as response:
            status = response.status
            payload = json.loads(response.read().decode("utf-8"))
            return status, payload
    except error.HTTPError as exc:
        payload = json.loads(exc.read().decode("utf-8"))
        return exc.code, payload


def _print_case(label: str, status: int, payload: dict) -> None:
    print(f"\n[{label}] status={status}")
    print(json.dumps(payload, indent=2, sort_keys=True))


def run(base_url: str) -> None:
    api = base_url.rstrip("/") + "/v1/admin"

    common_headers = {
        "X-BUSINESS-ID": DEV_BUSINESS_ID,
    }

    status, payload = _call(
        method="GET",
        url=f"{api}/feature-flags?business_id={DEV_BUSINESS_ID}",
        headers=common_headers,
    )
    _print_case("missing-key", status, payload)

    status, payload = _call(
        method="GET",
        url=f"{api}/feature-flags?business_id={DEV_BUSINESS_ID}",
        headers={**common_headers, "X-API-KEY": "invalid-key"},
    )
    _print_case("invalid-key", status, payload)

    status, payload = _call(
        method="GET",
        url=f"{api}/feature-flags?business_id=99999999-9999-9999-9999-999999999999",
        headers={
            "X-API-KEY": DEV_ADMIN_API_KEY,
            "X-BUSINESS-ID": "99999999-9999-9999-9999-999999999999",
        },
    )
    _print_case("unauthorized-business", status, payload)

    status, payload = _call(
        method="POST",
        url=f"{api}/feature-flags/set",
        headers={
            "X-API-KEY": DEV_CASHIER_API_KEY,
            "X-BUSINESS-ID": DEV_BUSINESS_ID,
            "X-BRANCH-ID": DEV_ADMIN_BRANCH_ID,
        },
        body={
            "business_id": DEV_BUSINESS_ID,
            "branch_id": DEV_ADMIN_BRANCH_ID,
            "flag_key": "ENABLE_DOCUMENT_DESIGNER",
            "status": "ENABLED",
        },
    )
    _print_case("unauthorized-branch", status, payload)

    status, payload = _call(
        method="POST",
        url=f"{api}/feature-flags/set",
        headers={
            "X-API-KEY": DEV_ADMIN_API_KEY,
            "X-BUSINESS-ID": DEV_BUSINESS_ID,
            "X-BRANCH-ID": DEV_ADMIN_BRANCH_ID,
        },
        body={
            "business_id": DEV_BUSINESS_ID,
            "branch_id": DEV_CASHIER_BRANCH_ID,
            "flag_key": "ENABLE_DOCUMENT_DESIGNER",
            "status": "ENABLED",
        },
    )
    _print_case("branch-mismatch", status, payload)

    status, payload = _call(
        method="POST",
        url=f"{api}/feature-flags/set",
        headers={
            "X-API-KEY": DEV_ADMIN_API_KEY,
            "X-BUSINESS-ID": DEV_BUSINESS_ID,
        },
        body={
            "business_id": DEV_BUSINESS_ID,
            "flag_key": "ENABLE_COMPLIANCE_ENGINE",
            "status": "ENABLED",
        },
    )
    _print_case("set-flag-success", status, payload)

    status, payload = _call(
        method="GET",
        url=f"{api}/feature-flags?business_id={DEV_BUSINESS_ID}",
        headers={
            "X-API-KEY": DEV_ADMIN_API_KEY,
            "X-BUSINESS-ID": DEV_BUSINESS_ID,
        },
    )
    _print_case("read-flags-success", status, payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Server base URL.",
    )
    args = parser.parse_args()
    run(args.base_url)


if __name__ == "__main__":
    main()

