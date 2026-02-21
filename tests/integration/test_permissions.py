"""
Tests — Integration Permissions
===================================
Controls who can configure and trigger integrations.
"""

from __future__ import annotations

import uuid

import pytest

from integration.permissions import (
    INTEGRATION_CONFIGURE,
    INTEGRATION_ENABLE,
    INTEGRATION_VIEW_AUDIT,
    IntegrationPermissionChecker,
)


BIZ = uuid.uuid4()
BIZ_OTHER = uuid.uuid4()


class TestIntegrationPermissions:
    def test_grant_and_check(self):
        checker = IntegrationPermissionChecker()
        checker.grant("admin-1", BIZ, frozenset([INTEGRATION_CONFIGURE, INTEGRATION_ENABLE]))
        assert checker.check("admin-1", BIZ, INTEGRATION_CONFIGURE) is True
        assert checker.check("admin-1", BIZ, INTEGRATION_ENABLE) is True

    def test_deny_ungrantd_permission(self):
        checker = IntegrationPermissionChecker()
        checker.grant("admin-1", BIZ, frozenset([INTEGRATION_CONFIGURE]))
        assert checker.check("admin-1", BIZ, INTEGRATION_VIEW_AUDIT) is False

    def test_deny_unknown_actor(self):
        checker = IntegrationPermissionChecker()
        assert checker.check("nobody", BIZ, INTEGRATION_CONFIGURE) is False

    def test_tenant_isolation(self):
        checker = IntegrationPermissionChecker()
        checker.grant("admin-1", BIZ, frozenset([INTEGRATION_CONFIGURE]))
        # Same actor, different business → denied
        assert checker.check("admin-1", BIZ_OTHER, INTEGRATION_CONFIGURE) is False

    def test_revoke(self):
        checker = IntegrationPermissionChecker()
        checker.grant("admin-1", BIZ, frozenset([INTEGRATION_CONFIGURE]))
        assert checker.check("admin-1", BIZ, INTEGRATION_CONFIGURE) is True
        checker.revoke("admin-1", BIZ)
        assert checker.check("admin-1", BIZ, INTEGRATION_CONFIGURE) is False
