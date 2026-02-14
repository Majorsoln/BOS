BOS Scope + Actor Matrix

Version: v1.0
Phase: 0 — Identity Boundary
Status: Constitutional

1️⃣ Actor Requirement Levels
Default Rule

All commands are:

ACTOR_REQUIRED


Unless explicitly declared:

SYSTEM_ALLOWED

2️⃣ Actor Types (v1 Minimal)
Actor Type	Description
USER	Human user
SYSTEM	Internal kernel operation
SERVICE	Trusted internal service
3️⃣ Scope + Actor Enforcement Matrix
🧱 Core Kernel Operations
Command Type	Scope	Actor Requirement
Replay (business scoped)	BUSINESS	SYSTEM_ALLOWED
Replay (unscoped)	UNSCOPED	SYSTEM_ALLOWED
Bootstrap self-check	BUSINESS	SYSTEM_ALLOWED
Engine registry init	BUSINESS	SYSTEM_ALLOWED

Reason: These are infrastructure-level.

👤 Identity & Actor Commands
Command	Scope	Actor
Create Actor	BUSINESS	SYSTEM_ALLOWED
Assign Role	BUSINESS	ACTOR_REQUIRED
Deactivate Actor	BUSINESS	ACTOR_REQUIRED
🏢 Business-Level Administrative Commands
Command	Scope	Actor
Create Branch	BUSINESS	ACTOR_REQUIRED
Update Business Profile	BUSINESS	ACTOR_REQUIRED
Configure Compliance Profile	BUSINESS	ACTOR_REQUIRED

Actor must be authorized for business.

🏬 Branch-Scoped Operational Commands
Command	Scope	Actor
POS Sale	BRANCH_REQUIRED	ACTOR_REQUIRED
Cash Drawer Open	BRANCH_REQUIRED	ACTOR_REQUIRED
Inventory Movement	BRANCH_REQUIRED	ACTOR_REQUIRED
Workshop Production Execute	BRANCH_REQUIRED	ACTOR_REQUIRED

Actor must:

Belong to business

Be authorized for branch

Match branch context

📄 Document Engine
Command	Scope	Actor
Create Template	BUSINESS	ACTOR_REQUIRED
Issue Invoice (operational)	BRANCH_REQUIRED	ACTOR_REQUIRED
Generate Management Report	BUSINESS	ACTOR_REQUIRED
4️⃣ Authorization Rules (v1 Lightweight)

For ACTOR_REQUIRED:

Must Validate:

ActorContext present

actor_id valid

actor authorized for business_id

If branch scope:

actor authorized for branch_id

v1 Implementation:

Authorization hook/stub allowed

No DB caching inside ActorContext

Deterministic behavior only

5️⃣ Explicit SYSTEM_ALLOWED Rule

SYSTEM_ALLOWED commands:

Must NOT require ActorContext

Must NOT accidentally accept user-supplied actor_id

Must remain auditable (system actor implicit or explicit)

6️⃣ Rejection Codes
Condition	Code
Missing actor	ACTOR_REQUIRED_MISSING
Invalid actor	ACTOR_INVALID
Business unauthorized	ACTOR_UNAUTHORIZED_BUSINESS
Branch unauthorized	ACTOR_UNAUTHORIZED_BRANCH

All rejections must be deterministic.

7️⃣ Replay Safety Rule

Replay MUST:

Not require ActorContext

Not re-run authorization checks

Not mutate actor state

Preserve event chain deterministically

Actor checks apply only to command execution path.

8️⃣ Constitutional Constraints

Identity layer must:

Not alter hash-chain logic

Not inject timestamps

Not use randomness

Not call external systems

Be additive-only

🔐 Final Doctrine Alignment

After this phase:

BusinessContext → enforces tenant boundary
ActorContext → enforces identity boundary
Policy Engine → enforces authorization boundary

No operation exists outside these three layers.