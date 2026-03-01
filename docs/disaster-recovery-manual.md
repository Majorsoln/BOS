# BOS Disaster Recovery Manual

> Version: 1.0
> Audience: Operations teams and system administrators

---

## 1. Architecture Advantages for Recovery

BOS's event-sourced architecture provides inherent recovery guarantees:

- **Event Store is immutable** — Events are never modified or deleted
- **Hash-chain integrity** — Tampering is detectable via SHA-256 chain
- **Projections are disposable** — Rebuilt from events at any time
- **Deterministic replay** — Same events always produce identical state
- **Corrections, not updates** — Errors are corrected by new events, not mutations

---

## 2. Resilience Modes

BOS operates in three resilience modes (`core/resilience/`):

| Mode | Description | Allowed Operations |
|------|-------------|-------------------|
| **NORMAL** | Full operation | All read + write |
| **DEGRADED** | Partial operation | Read + limited write |
| **READ_ONLY** | Maintenance/recovery | Read only, no writes |

### 2.1 Mode Transitions

```
NORMAL ──→ DEGRADED ──→ READ_ONLY
  ▲            │              │
  └────────────┴──────────────┘
        (recovery complete)
```

### 2.2 Triggering Mode Changes

Mode changes are administrative actions:
1. Set resilience mode via system property
2. All command dispatchers check mode before execution
3. In DEGRADED mode, non-essential engines can be disabled via feature flags
4. In READ_ONLY mode, all write commands are rejected

---

## 3. Event Store Recovery

### 3.1 Hash-Chain Verification

The event store maintains a SHA-256 hash chain. Each event's hash includes:
- Previous event hash
- Event type
- Business ID
- Payload content

**Verification procedure:**

1. Read events in sequence
2. Recompute hash for each event
3. Compare with stored `event_hash`
4. If mismatch detected → flag corrupt event

```
Event N-1: hash = SHA256(prev_hash + event_data) → stored_hash ✓
Event N:   hash = SHA256(event_N-1_hash + event_data) → stored_hash ✓
Event N+1: hash = SHA256(event_N_hash + event_data) → MISMATCH ✗ ← corruption
```

### 3.2 Replay Procedure

To rebuild all state from events:

1. Set system to **READ_ONLY** mode
2. Clear all projection stores (in-memory state)
3. Load all events from Event Store in order
4. Replay each event through its projection's `apply()` method
5. Verify projection state matches expected counts
6. Restore to **NORMAL** mode

```python
# Conceptual replay
projection_store.truncate()
for event in event_store.read_all(business_id, order_by="created_at"):
    projection_store.apply(event.event_type, event.payload)
```

### 3.3 Selective Replay

Replay can be scoped:
- **Per business** — Rebuild one tenant's state
- **Per engine** — Rebuild one engine's projections
- **Per time range** — Replay events from a specific point
- **From snapshot** — Start from a known-good snapshot, replay only new events

---

## 4. Snapshot Recovery

### 4.1 Snapshot Storage

Snapshots (`core/event_store/snapshot_storage.py`) capture projection state at a point in time:

- **Append-only** — Snapshots are never overwritten
- **Time-travel** — Query snapshots at any historical point
- **Tenant-isolated** — Each business has its own snapshot history

### 4.2 Recovery from Snapshot

1. Load the latest valid snapshot for the business
2. Restore projection state from snapshot data
3. Query events created AFTER the snapshot timestamp
4. Replay only those new events
5. Verify final state

This is faster than full replay for large event histories.

---

## 5. Data Backup Strategy

### 5.1 Event Store Backup

The Event Store (PostgreSQL) is the **single source of truth**:

- **Full backup**: `pg_dump` of the event store tables
- **Frequency**: Daily full backup + continuous WAL archiving
- **Retention**: Based on `audit.retention_days` system property (default: 365)
- **Verification**: Restore to staging, run hash-chain verification

### 5.2 What Does NOT Need Backup

- **Projections** — Disposable, rebuilt from events
- **Cache** — TTL-based, rebuilt on miss
- **Feature flag state** — Stored as events, rebuilt on replay
- **Admin config** — Stored as events, rebuilt on replay

### 5.3 Backup Verification Checklist

- [ ] Backup completes without error
- [ ] Backup can be restored to a clean database
- [ ] Hash-chain verification passes after restore
- [ ] Projection rebuild produces consistent state
- [ ] Event count matches expected total
- [ ] Tenant isolation intact (no cross-tenant data leaks)

---

## 6. Failure Scenarios & Recovery

### 6.1 Database Corruption

**Symptoms:** Hash-chain verification fails, queries return errors

**Recovery:**
1. Switch to READ_ONLY mode
2. Restore database from last verified backup
3. Run hash-chain verification
4. Replay any events from WAL archive since backup
5. Rebuild projections
6. Verify state, return to NORMAL

### 6.2 Projection Inconsistency

**Symptoms:** Projection queries return incorrect data, counts don't match

**Recovery:**
1. Truncate affected projection store
2. Replay all events for that engine
3. Verify rebuilt state
4. No data loss — events are intact

This is the simplest recovery since projections are disposable.

### 6.3 Partial Write Failure

**Symptoms:** Event persisted but projection not updated

**Recovery:**
- On next startup, projection rebuilds from all events
- The missed event will be applied during rebuild
- No manual intervention required

### 6.4 Tenant Data Isolation Breach

**Symptoms:** Cross-tenant data visible in queries

**Recovery:**
1. Immediately set affected tenants to READ_ONLY
2. Audit event store for cross-tenant events (should never exist)
3. Review scope guard enforcement
4. If events are correctly scoped, rebuild projections (likely a projection bug)
5. Fix and deploy, then restore NORMAL mode

---

## 7. Health Checks

### 7.1 Dashboard Health Status

The admin dashboard (`core/admin/dashboard.py`) provides:

```python
health = dashboard.get_health_status(
    resilience_mode="NORMAL",
    projection_count=15,
    unhealthy_projections=[],
    cache_hit_rate=0.95,
)
# Returns: HealthStatus(is_healthy=True, ...)
```

### 7.2 Health Indicators

| Indicator | Healthy | Warning | Critical |
|-----------|---------|---------|----------|
| Resilience Mode | NORMAL | DEGRADED | READ_ONLY |
| Unhealthy Projections | 0 | 1-2 | 3+ |
| Cache Hit Rate | > 80% | 50-80% | < 50% |
| Event Store | Writable | Slow | Unreachable |

### 7.3 Monitoring Metrics

The metrics collector (`projections/metrics/`) tracks:

- Events processed per second
- Projection rebuild duration
- Average and peak event apply time
- Cache utilization and eviction rates

---

## 8. Recovery Checklist

### Pre-Recovery
- [ ] Identify failure type (DB corruption, projection inconsistency, etc.)
- [ ] Set affected systems to READ_ONLY mode
- [ ] Notify stakeholders of maintenance window
- [ ] Document the incident timeline

### During Recovery
- [ ] Restore data from backup (if database corruption)
- [ ] Run hash-chain verification
- [ ] Rebuild affected projections
- [ ] Verify event counts per tenant
- [ ] Test critical operations on staging

### Post-Recovery
- [ ] Run full test suite
- [ ] Verify tenant isolation
- [ ] Restore to NORMAL mode
- [ ] Monitor health dashboard for 24 hours
- [ ] Document root cause and prevention measures

---

*"Events are truth. Projections are disposable. Recovery is deterministic."*
