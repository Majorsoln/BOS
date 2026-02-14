BOS Scope & Tenant Boundary Policy

Version: v1.0
Status: Constitutional (Phase 0 Enforcement Layer)
Applies to: All engines, commands, events, projections

1. Purpose

This document defines the official scope model for BOS.

BOS is a deterministic, multi-tenant, event-sourced kernel.
Tenant boundary must be enforced consistently and permanently.

This policy establishes:

Required scope identifiers

Meaning of business-level vs branch-level scope

Scope requirements per engine

Enforcement model

Rejection rules

2. Core Scope Model
2.1 Required Fields

Every command and event MUST contain:

business_id (mandatory)
branch_id (optional)

2.2 Scope Semantics
Business Scope
business_id = X
branch_id = None


Meaning:

Operation applies at business-wide level.

Aggregated or administrative scope.

No implicit branch inference allowed.

Branch Scope
business_id = X
branch_id = Y


Meaning:

Operation is isolated to specific branch.

Physical/operational effects usually occur here.

2.3 Prohibited Semantics

The system must NEVER:

Infer branch automatically.

Default branch silently.

Allow cross-business access.

Mutate state outside scope validation.

3. Scope Requirements Declaration

Each command MUST declare:

scope_requirement = BUSINESS_ALLOWED
or
scope_requirement = BRANCH_REQUIRED


Future extension allowed:

LOCATION_REQUIRED


(Not active in v1.)

4. Enforcement Rules
4.1 Business Boundary Rule

If:

command.business_id != aggregate.business_id


→ Reject deterministically.

No cross-business operations allowed.

4.2 Branch Requirement Rule

If:

scope_requirement == BRANCH_REQUIRED
and branch_id is None


→ Reject deterministically.

4.3 Cross-Branch Protection

If:

aggregate.branch_id != command.branch_id
and aggregate.branch_id is not None


→ Reject deterministically.

4.4 Event Store Guard

Before appending event:

Validate business_id exists.

Validate scope consistency.

Reject orphaned events.

5. Engine Scope Requirements Matrix
5.1 Core Kernel
Component	Business	Branch
Command Bus	Allowed	Allowed
Policy Engine	Allowed	Allowed
Event Store	Allowed	Allowed
Replay	Allowed	Allowed
5.2 Identity & Actors
Action	Business	Branch
Create Business	Required	Not allowed
Create Branch	Required	Not allowed
Register User	Allowed	Allowed
Assign Role	Allowed	Allowed
5.3 Permissions
Action	Business	Branch
Admin configuration	Allowed	Limited override
Operational actions	Not allowed	Required
Reporting view	Allowed	Allowed
5.4 Document Engine
Action	Business	Branch
Create template	Allowed	Allowed
Activate template	Allowed	Allowed
Issue sales document (POS)	Not allowed	Required
Business-level document (e.g. management report)	Allowed	Allowed
5.5 Compliance Engine
Action	Business	Branch
Assign compliance profile	Allowed	Allowed
Transaction validation	Conditional	Required if operational
5.6 Accounting Engine
Action	Business	Branch
Journal posting	Allowed	Allowed
Period close	Required	Not allowed
Financial reports	Allowed	Allowed
5.7 Cash Management Engine
Action	Business	Branch
Create bank account	Allowed	Allowed
Create drawer	Not allowed	Required
CashIn/CashOut	Not allowed	Required
Reconciliation	Not allowed	Required
5.8 Inventory Engine
Action	Business	Branch
Stock movement	Not allowed	Required
Stock valuation view	Allowed	Allowed
5.9 Procurement Engine
Action	Business	Branch
Supplier registry	Allowed	Allowed
Goods receipt	Not allowed	Required
5.10 Retail & Restaurant Modules

All operational transactions:

scope_requirement = BRANCH_REQUIRED

5.11 Workshop Module
Action	Business	Branch
Style catalog	Allowed	Allowed
Production execution	Not allowed	Required
Material consumption	Not allowed	Required
6. Determinism Guarantee

Scope enforcement must:

Produce explicit rejection outcome.

Never auto-correct scope.

Never silently downgrade branch requirement.

Remain replay-safe.

Replay of historical events must preserve original scope.

7. Additive Expansion Strategy

Future hierarchical expansion allowed:

business → branch → location → counter


But:

Not part of v1.

Must not break existing semantics.

Must be additive only.

8. Testing Requirements

Every scope rule must have tests for:

Missing branch when required.

Cross-branch access attempt.

Cross-business access attempt.

Business-level allowed operation.

Replay consistency.

9. Constitutional Clause

This Scope Policy is foundational.

All future engines, modules, integrations, and AI layers must comply.

No exceptions allowed.