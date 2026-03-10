"""
Management command: bootstrap_dev

Creates the dev business, branches, actors, and API keys needed for local
development.  Safe to run multiple times — skips anything that already exists.

Usage:
    python manage.py bootstrap_dev
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create dev business, branches, actors, and API keys for local development"

    def handle(self, *args, **options):
        from adapters.django_api.wiring import (
            DEV_ADMIN_API_KEY,
            DEV_BUSINESS_ID,
            DEV_ADMIN_BRANCH_ID,
            DEV_CASHIER_BRANCH_ID,
            DEV_CASHIER_API_KEY,
            _ensure_dev_identity_records,
            _ensure_dev_api_key_credentials,
        )

        self.stdout.write("Bootstrapping dev environment...")

        _ensure_dev_identity_records()
        self.stdout.write(self.style.SUCCESS(
            f"  Business:  {DEV_BUSINESS_ID}  (BOS Dev Business)"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  Branch 1:  {DEV_ADMIN_BRANCH_ID}  (ADMIN)"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  Branch 2:  {DEV_CASHIER_BRANCH_ID}  (CASHIER)"
        ))

        _ensure_dev_api_key_credentials()
        self.stdout.write(self.style.SUCCESS(
            f"  Admin key: {DEV_ADMIN_API_KEY}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  Cashier:   {DEV_CASHIER_API_KEY}"
        ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done! Dev environment ready."))
        self.stdout.write(f"  Frontend login → Business ID: {DEV_BUSINESS_ID}")
        self.stdout.write(f"  Frontend login → API Key:     {DEV_ADMIN_API_KEY}")
