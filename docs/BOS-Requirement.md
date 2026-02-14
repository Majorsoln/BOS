BOS Scope Requirement Table (v1)
Legend

✅ Allowed

❌ Not allowed / reject

⚠️ Allowed but with extra rule/guard

“Default”: kama branch haipo, mfumo utatumia business scope bila kukisia branch.

1) Core Kernel Layer
Component	Business scope (branch=None)	Branch scope (branch=id)	Notes
Command Bus / Dispatcher	✅	✅	Must always carry BusinessContext
Policy Engine	✅	✅	Policies can require branch per command
Event Store Append	✅	✅	Event must include business_id; branch_id stored as null or id
Replay Engine	✅	✅	Replay must preserve scope fields exactly
Engine Registry/Contracts	✅	✅	Contract checks independent of scope
2) Identity & Actor System (Phase 0 gap #2)
Entity/Action	Business	Branch	Notes
Create Business	✅	❌	Business creation is global/system-admin
Create Branch	✅	❌	Branch created within business scope
Register User/Actor	✅	✅	Actors are business-owned; branch binding optional
Assign Role	✅	✅	Role assignment can be business-wide or branch-scoped
Login/Auth events	✅	✅	Auth events must be business-scoped at least
3) Permissions (Role → Permission → Scope)
Permission type	Business	Branch	Notes
Admin/global policy change	✅	⚠️	Usually business-level; branch override allowed for limited settings
Operational actions (POS, stock move)	❌	✅	Must be branch-scoped
Reporting view	✅	✅	Business-wide reports allowed; branch filter optional
Template management	✅	✅	Default business-level; branch override allowed
4) Document Engine (Strict Builder + HTML+PDF)
Action	Business	Branch	Notes
Create template	✅	✅	Default to business; optional branch version
Activate template	✅	✅	Business default + branch override
Issue document (Invoice/Receipt/Quote…)	⚠️	✅	Allowed business-scope ONLY for non-branch flows; otherwise require branch (see rules)
Document numbering policy	✅	✅	Policy decides per-business or per-branch sequence
Verification (hash check)	✅	✅	Always allowed with proper scope

Rule: Issuing “sales documents” (receipt/invoice) in POS context must be branch-scoped.

5) Compliance Engine (Admin-driven, no country code)
Action	Business	Branch	Notes
Assign compliance profile	✅	✅	Business default; optional branch override
Validate template vs compliance	✅	✅	Branch-specific constraints may apply
Validate transaction vs compliance	⚠️	✅	If compliance requires branch-level identity, reject business-scope
Produce statutory export/report	✅	✅	Output may require branch grouping
6) Accounting Engine (Double Entry)
Action	Business	Branch	Notes
Post journal entries	✅	✅	Can be business-level; branch tagging optional
Close period	✅	❌	Period close is business-level governance
Trial balance / P&L	✅	✅	Business-wide and branch views
Corrections	✅	✅	Corrections are new events; scope preserved

Rule: Accounting supports both; branch is analytical dimension, not always required.

7) Cash Management Engine (CME)
Action	Business	Branch	Notes
Create cash container (drawer/bank/wallet)	⚠️	✅	Bank can be business-level; drawer must be branch
CashIn/CashOut (operational)	❌	✅	Cash ops require branch
Transfer between containers	⚠️	✅	Business-level transfers allowed only between business-level containers (e.g. bank↔wallet)
Reconciliation (drawer close)	❌	✅	Must be branch
Adjustments	❌	✅	Must be branch + approval

Rule: Drawers are never business-scope.

8) Inventory Engine
Action	Business	Branch	Notes
Stock movement (in/out/transfer)	❌	✅	Always branch-scoped
Stock valuation	✅	✅	Business-wide view allowed; derived from branch movements
Reorder rules	✅	✅	Business default; branch thresholds optional

Rule: Inventory truth happens at branch.

9) Procurement Engine
Action	Business	Branch	Notes
Supplier registry	✅	✅	Usually business-level
Requisition	✅	✅	Can be business or branch initiated
Purchase Order	⚠️	✅	If delivery is to branch, require branch
Goods Receipt	❌	✅	Always branch (inventory impact)
Supplier invoice matching	✅	✅	Branch tag optional; depends on GRN
10) Retail Module (POS)
Action	Business	Branch	Notes
POS sale	❌	✅	Always branch
Refund/return	❌	✅	Always branch
Remote item list manage	✅	✅	Business default + branch overrides
Promotions	✅	✅	Business default; branch override allowed
11) Restaurant Module
Action	Business	Branch	Notes
Table/room mapping	❌	✅	Branch (restaurant location)
QR self-service order	❌	✅	Branch
Kitchen workflow	❌	✅	Branch
Split billing	❌	✅	Branch
12) Workshop Module (Windows/Doors/Panels)
Action	Business	Branch	Notes
Style catalog management	✅	✅	Business default; branch override allowed
Quote generation	✅	✅	Quote can be business/branch; production requires branch
Cutting optimization run	❌	✅	Production impacts inventory → branch required
Material reservation/consumption	❌	✅	Always branch
Offcut tracking	❌	✅	Always branch
13) Reporting & BI Engine
Action	Business	Branch	Notes
KPI dashboards	✅	✅	Business + branch filter
Snapshot export	✅	✅	Must respect scope
Audit explorer	✅	✅	Must scope queries strictly
✅ Global Policy Rules (Universal)

business_id always required for every command/event.

branch_id=None is valid and intentional (business scope).

Any action that changes physical reality (cash drawer, stock move, kitchen order, workshop production) is branch required.

“Administrative truth” (templates, compliance profiles, accounting close, reporting) can be business-scope with optional branch overrides.

No implicit branch guessing. Ever.