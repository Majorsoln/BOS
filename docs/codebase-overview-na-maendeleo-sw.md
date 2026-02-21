# BOS: Ufafanuzi wa Codebase + Mpango wa Kumalizia Phase 12 na 13

Hii ni toleo lililoboreshwa la maelezo ya BOS kwa Kiswahili, lenye:
1. Uelewa wa ndani wa codebase,
2. Mtiririko halisi wa Command → Outcome → Event,
3. Maendeleo ya sasa,
4. Mpango unaotekelezeka wa kumalizia Phase 12 (SaaS Productization) na Phase 13 (Documentation).

---

## 1) BOS ni nini kwa lugha rahisi

BOS ni **kernel ya biashara** yenye sheria kuu mbili:
- Kila kinachobadilika kwenye mfumo kinaingia kama **event** (si mutation ya siri),
- Matokeo lazima yawe **deterministic** (ukirudia input + replay, upate state ileile).

Hii inafanya BOS iwe:
- rahisi kufanya audit,
- salama kwa multi-tenant,
- na inayoaminika kisheria (replay + hash-chain).

---

## 2) Jinsi codebase imejengwa (ramani ya kueleweka haraka)

### 2.1 `core/` — moyo wa kernel

- `core/commands/`
  - Hapa ndipo command huingia, hukaguliwa, na kupewa outcome (accepted/rejected).
- `core/event_store/`
  - Huhifadhi events kwa mtindo wa append-only na kulinda integrity ya hash-chain.
- `core/events/`
  - Registry/dispatcher ya event handlers.
- `core/replay/`
  - Hurejesha state kwa replay ya events ili kuhakikisha reproducibility.
- `core/context/`
  - `BusinessContext`, scope guard, actor context (tenant safety).
- `core/engines/`
  - Registry na enforcement ya isolation kati ya engines.
- `core/feature_flags/`
  - Kuwasha/kuzima engines au uwezo fulani kwa njia ya sera.
- `core/security/`
  - Tenant isolation, rate limit, anomaly detection.

### 2.2 `engines/` — uwezo wa biashara

Engines zilizopo ni pamoja na: accounting, cash, inventory, procurement, retail, restaurant, workshop, promotion, hr, reporting.

Pattern ya kawaida kwa engine:
- `events.py`
- `commands/`
- `services/`
- `policies/`
- `subscriptions.py`

Hii inaweka consistency ya usanifu na urahisi wa replay.

### 2.3 `ai/` — ushauri, si mamlaka ya state

- AI guardrails
- advisors
- decision journal
- decision simulation

Kanuni: AI haiandiki state moja kwa moja; inashauri tu.

### 2.4 `integration/` + `adapters/`

- Inbound adapters: kupokea matukio/requests kutoka nje,
- Outbound publishers: kutuma events nje,
- Integration audit log + permissions.

---

## 3) Mtiririko halisi wa write path (kwanini ni salama)

1. Request hujengwa kuwa **Command** ndani ya `BusinessContext`.
2. Validation + policy checks hufanyika.
3. Mfumo hurudisha **Outcome** (accepted/rejected + sababu wazi).
4. Accepted outcome huzaa **Event** na kuandikwa append-only.
5. Projections/subscribers husasishwa kupitia events.
6. Ukifanya replay ya events hizo, unapaswa kupata state ileile.

Faida kuu:
- hakuna hidden mutation,
- hakuna cross-tenant leak,
- hakuna “silent failure” (rejections ni explicit).

---

## 4) Maendeleo ya sasa (snapshot)

Kulingana na `DEVSTATE.md`:
- Phase 0 hadi 11: **zimekamilika**,
- Phase 12 (SaaS Productization): **imeanza kwa implementation ya Billing Engine msingi (plan/subscription/payment/suspension/renewal)**,
- Phase 13 (Documentation): **haijaanza**.

Maana yake: msingi wa kernel, engines, security, integration, na enterprise admin tayari upo; kilichobaki ni kufunga bidhaa kuwa SaaS kamili na kukamilisha docs za matumizi/developer.

### Kimeanza kutekelezwa sasa (sio maelezo tu)
- Engine mpya ya `billing` imeongezwa kwenye repo ikiwa na `commands`, `events`, `policies`, `services`, na `subscriptions`, pamoja na renewal flow.
- Feature flag mapping imeongezwa kwa command zote za billing.
- Tests za engine (`tests/engines/test_billing_engine.py`) zina-cover command validation, full event flow, na boundary ya subscription existence.

---

## 5) “Malizia phase hizo” — Mpango wa utekelezaji wa Phase 12 na 13

## 5.1 Phase 12 — SaaS Productization (hatua za kujenga)

### A) Tenant onboarding flow
- Tengeneza onboarding command set (create tenant profile, default branch, default settings).
- Hakikisha kila hatua ina event yake na rejection outcomes wazi.
- Weka idempotency key kwenye onboarding endpoints.

### B) Subscription & billing model
- Ongeza module ya billing iliyo event-sourced:
  - plan_assigned,
  - subscription_started,
  - subscription_renewed,
  - payment_recorded,
  - subscription_suspended.
- Usifunge sheria kwa nchi (`if country == "X"` hairuhusiwi); tumia config/policy.

### C) Tenant lifecycle automation
- Unganisha billing status na admin tenant state kupitia events (si direct mutation).
- Mfano: subscription expired → event → policy ya kuset READ_ONLY mode.

### D) Operational safety
- Rate limits kwa tier za plan,
- Usage metering projections (events/day, storage, API calls),
- Alerts za anomaly za billing/usage.

### E) Acceptance criteria ya Phase 12
- Tenant mpya anaweza ku-onboard bila manual DB updates,
- Billing state ina replay consistency,
- Cross-tenant isolation tests zinapita,
- Feature flags za SaaS modules default ziwe OFF hadi ziwashwe.

## 5.2 Phase 13 — Documentation (hatua za kukamilisha)

### A) Developer docs
- “How commands become events” (with sequence diagram),
- “How to add a new engine safely” checklist,
- “Replay safety & determinism pitfalls”.

### B) Operator/Admin docs
- Tenant lifecycle runbook,
- Incident response runbook (rate limit, anomaly, degraded/read-only modes),
- Backup/replay verification procedures.

### C) API docs
- Contracts + examples za auth/tenant scope,
- Error catalog (rejection codes + meanings),
- Idempotency and retry behavior.

### D) Compliance docs
- Audit trail explanation,
- Policy governance model,
- Evidence pack template kwa legal/financial audits.

### E) Acceptance criteria ya Phase 13
- Docs zote muhimu zipo ndani ya repo na zina versioning,
- Kila engine ina “quick start + policy boundary notes”,
- New engineer anaweza ku-run core tests na kuelewa architecture ndani ya muda mfupi.

---

## 6) Risks za kutazama wakati wa kumalizia

- Kuingiza logic ya billing nje ya event flow (hatari kubwa).
- Kuacha tenant context kwenye endpoint mpya.
- Kutegemea current time/random kwenye outcome logic.
- Kuweka integration shortcuts zinazovunja engine isolation.

Mitigation:
- enforce command validators,
- policy tests za tenant boundaries,
- replay tests kwa modules mpya,
- explicit rejection outcomes kila transition invalid.

---

## 7) Hitimisho

BOS ipo kwenye hatua nzuri sana ya msingi wa kernel. Ili “kumalizia phase hizo” kwa usalama:
- Phase 12 ijikite kwenye onboarding + billing + lifecycle automation kwa event-sourced model,
- Phase 13 ijikite kwenye docs za developer/operator/API/compliance zenye acceptance criteria wazi.

Kwa njia hii, utatunza utambulisho wa BOS kama deterministic, legally-defensible business kernel bila kuvunja doctrine zake.
