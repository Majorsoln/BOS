# BOS — Agent Operating Manual

This repository implements BOS Core:
A deterministic, event-sourced, engine-isolated Business Operating Kernel.

Architecture is frozen (additive changes only).

---

## 1. Core Doctrine (Non-Negotiable)

1. State is derived from events only.
2. Event store is append-only.
3. No hidden mutation.
4. Every outcome must be deterministic.
5. Replay must reproduce identical state.
6. Engines are isolated — no cross-engine direct mutation.
7. All write operations go through Command → Outcome → Event.
8. AI components are advisory only — never state-authoritative.

---

## 2. Determinism Rules

DO NOT:
- Use random()
- Use current time inside outcome logic
- Use non-deterministic ordering
- Mutate state outside event append
- Modify past events

If time is required:
- It must be passed explicitly as part of the command.

---

## 3. Multi-Tenant Safety (Mandatory)

All commands MUST execute within BusinessContext.

Every event MUST contain:
- business_id
- branch_id (if applicable)

Cross-tenant access must fail deterministically.

Never allow implicit global access.

---

## 4. Engine Isolation

Engines must:
- Communicate only via events
- Never call each other’s internals directly
- Never mutate another engine’s state

If coordination is needed:
- Emit event
- Let subscriber react

---

## 5. Event Store Rules

- Append-only.
- Hash-chain integrity must remain intact.
- No event deletion.
- Corrections must be new events.

Replay must:
- Reproduce exact state.
- Not depend on external systems.

---

## 6. Command Design Rules

Every command must:
- Validate input
- Produce deterministic outcome
- Emit explicit events
- Fail explicitly (rejection outcome) if invalid

Never:
- Modify DB directly.
- Skip validation layer.

---

## 7. Policy Layer Rules

Policies must:
- Enforce boundaries (tenant, permission, invariants)
- Reject invalid transitions explicitly
- Be test-covered

Policies must not:
- Mutate state
- Hide failure

---

## 8. Testing Discipline

Before finalizing any change:

Run:

pytest tests/core/test_commands.py
pytest tests/core/test_policy.py
pytest tests/core/test_engine_registry.py

All tests must pass.

Add new tests for:
- Boundary enforcement
- Determinism
- Replay consistency
- Tenant isolation

---

## 9. Additive Architecture Only

You may:
- Add new modules
- Add new engines
- Add new events
- Add new policies

You may NOT:
- Remove core invariants
- Modify hash-chain logic
- Break replay
- Change existing contracts without versioning

---

## 10. Compliance Strategy

There must never be:
if country == "X":

All regional differences must be:
- Admin-configurable
- Policy-driven
- Data-defined

---

## 11. Document Engine Rules (When Implemented)

- Templates are structured JSON (no raw HTML injection).
- Past documents immutable.
- Render must be reproducible.
- PDF + HTML derived from same snapshot.

---

## 12. Workshop Engine Rules

- Parametric geometry only.
- No free drawing.
- No randomness in optimization.
- Same input → same cutting list.

---

## 13. Logging & Errors

Errors must:
- Be explicit.
- Not leak cross-tenant data.
- Be safe for audit.

---

## 14. Feature Flags

All new major engines must:
- Be wrapped behind feature flags.
- Default to OFF unless activated.

---

## 15. Before Submitting Changes

Provide:
1. Summary of changes
2. List of modified files
3. Test results
4. Confirmation of determinism
5. Confirmation of replay safety

---

BOS is not an ERP.
It is a deterministic, legally defensible business kernel.

All changes must preserve that identity.
