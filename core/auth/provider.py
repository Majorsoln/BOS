"""
BOS Auth - DB-backed Auth Provider
==================================
Resolves API keys from persistent credential storage.
"""

from __future__ import annotations

from core.auth.models import ApiKeyStatus
from core.auth.service import hash_api_key
from core.http_api.auth.provider import AuthPrincipal, AuthProvider


class DbAuthProvider(AuthProvider):
    def resolve_api_key(self, api_key: str) -> AuthPrincipal | None:
        if not isinstance(api_key, str) or not api_key.strip():
            return None

        from core.auth.models import ApiKeyCredential

        key_hash = hash_api_key(api_key)
        credential = (
            ApiKeyCredential.objects.filter(
                key_hash=key_hash,
                status=ApiKeyStatus.ACTIVE,
            )
            .order_by("created_at", "id")
            .first()
        )
        if credential is None:
            return None

        return AuthPrincipal(
            actor_id=credential.actor_id,
            actor_type=credential.actor_type,
            allowed_business_ids=tuple(credential.allowed_business_ids),
            allowed_branch_ids_by_business={
                business_id: tuple(branch_ids)
                for business_id, branch_ids in dict(
                    credential.allowed_branch_ids_by_business
                ).items()
            },
        )
