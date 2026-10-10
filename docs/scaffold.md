# Red Arc Ops Platform — Scaffold v1

**Status:** Agreed in chat 2026-10-08 (Zak + Claude). Nothing built. This is the
design the "ambitious branch" builds against. It merges:

- `Red Arc Custom CRM and Operations Platform Wish List.docx` (Zak, 2026-10-08)
- `data-model-v2.md` (2026-10-08), `regulated-entities-spec-v1.md`,
  `container-types-spec-v1.md`, `vendor-cost-scope-v0.md` (Cowork → Red Arc
  Systems Buildout)
- the existing Zoho-backed print tool in this repo (its print engine and Claude
  helpers carry over; its Zoho client does not)

Where the wish list and data model v2 disagree, this document wins and says why.

**Still owed before build starts:** waste category / treatment list and vendor
process codes (Zak). They gate slices 2 and 4.

---

## 0. Design rules

1. **Table only where it earns it.** A table exists when other records point at
   it or it carries a lifecycle/status. Anything static and 1:1 with a parent is
   a child row (what Zoho calls a subform).
2. **One state machine per thing.** Never two status fields kept in sync by
   triggers. Where two records show the same stage, one of them derives it.
3. **Snapshot money.** Cost and price are written onto the line when quoted and
   only refreshed by a deliberate action. Rates and fees are overwritten in
   place; history that matters lives on the lines.
4. **Enforce the workflow, allow the exception.** Gates block; warnings flag.
   Every override is audited.
5. **Boring tools.** Django LTS, Postgres, HTMX, Cloud Run. No clever
   infrastructure.

---

## 1. Object map

### CRM

| Table | Holds | Child rows | Notes |
|---|---|---|---|
| **Account** | Every business/person Red Arc deals with. Type: Prospect / Customer / Vendor / Partner | Account Team (user, role) · Contract Prices (category, billing unit, price, term) · Vendor Fees (name, type, applies to, rate, facility) | **Prospect is a type, not a table.** `prospect_stage` + `disqualified_reason` live here. Conversion = flip type, enforce customer-required fields. `contract_pricing_expected` flag (see §3). `status` Active / Inactive / Credit Hold. |
| **Contact** | People | — | Account-wide roles multi-select per RE spec §3 |
| **Regulated Entity** | Sites: generator, transporter, transfer yard, destination facility | Site Contacts (contact, roles) · 3rd-Party LTL Rates (billing unit, rate) — destination facilities only | Fields exactly per `regulated-entities-spec-v1.md`. Destination facilities add Delivery Method + Hub. |
| **Opportunity** | Sales pipeline | — | Stages: Identified → Technical Review → Estimate Created → Secondary Review → Closed Won / Closed Lost. Relates to an Account (any type) and optionally one Job. |
| **Activity** | One call, email, meeting or site visit | Tags (many-to-many to a Tag table) | One table, `type` picks the status set (§2). Account required; Contact, Opportunity, Job, Regulated Entity optional. Owner, scheduled/completed times, outcome notes. Timeline on every record it links to. |
| **Cadence** | A step-by-step outreach process | Cadence Steps (order, day offset, activity type, template) | Target type (prospect / customer), active flag |
| **Cadence Enrollment** | One account or contact running one cadence | — | Started, current step, status Active / Paused / Completed / Exited + reason |
| **Template** | Email body or call script with merge fields | — | Referenced by Cadence Steps; reusable across cadences |

### Libraries (reference data, admin-edited, seeded from public sources)

| Table | Source |
|---|---|
| **Hazmat Entry** — UN number, proper shipping name (with a `print_as` override for the italics/"or" problem), hazard class, packing group, ERG guide number, RQ | DOT Hazardous Materials Table (49 CFR 172.101), ERG |
| **RCRA Code** (D/F/K/P/U, with LDR treatment standard reference) | 40 CFR 261 / 268 |
| **Management Method Code** (incl. S codes) | EPA e-Manifest / BR |
| **Form Code**, **Source Code** | EPA BR |
| **NAICS Code** | Census |
| **Texas Waste Code Component** (sequence rules, form/classification) | TCEQ |
| **Exemption**, **Exclusion** | Zak supplies |
| **Waste Category** | Zak supplies (treatment × form) |

### Waste

| Table | Holds | Child rows | Notes |
|---|---|---|---|
| **Profile** | A generator's waste stream | Constituents (name, CAS, %, min/max) · Attachments | Status: Draft → Submitted → Approved → Expired. Sections per wish list minus Approval Info (that's the related Approvals list). One scrolling form, not tabs. |
| **TSDF Approval** | A TSDF's acceptance of a stream | Pricing Exceptions (billing unit, cost override, price/margin override, reason) | Generator (required), Profile (optional — blank for lab pack approvals), Vendor Price Line (sets TSDF + cost), approval #, expiration, status, manifest description fields, pallet manifest style. |
| **Lab Pack Inventory** | One drum (packing list) | Items (item #, product name, constituents, primary/secondary class, qty, container material, state, EPA codes, notes) | Generator, approval, user label (LP01…), system sequence number, DOT description, waste codes, container type, packing medium, LDR statement. Item autocomplete from prior entries (beta). lab-pack-sorter output is the import format. |

### Pricing (cost editors: Zak, Jessica, Suhail; everyone else read-only)

| Table | Holds | Child rows |
|---|---|---|
| **Container Type** | Per `container-types-spec-v1.md`, ported as-is (36 seed records, Carrier flag, handling multiplier) | — |
| **Vendor Price Line** | One line on a vendor's price sheet at one facility | Unit Rates (billing unit, vendor cost, vendor minimum) |
| **Service Item** | Labor, trucking, supplies, $35 LTL handling, etc. | — |

### Operations

| Table | Holds | Child rows | Notes |
|---|---|---|---|
| **Job** | One pickup or one day of work | Waste Lines (approval *or* lab pack inventory *or* category-only at estimate; container type; qty; est. weight; assumed delivery mode; cost + price snapshot; price source; flags) · Service Lines (service item, qty, price) | Type: Containerized LTL · Containerized Direct · Bulk · Transportation Only · Field Service · Training · Sampling/Analytical. Opportunity optional. Project optional. Stage set chosen by type (§2). |
| **Shipping Document** | One manifest or BOL | Lines (DOT description, approval/inventory, container count + code, total qty + unit, handling code, print flags) | Type: HW Manifest (8700-22) · Non-Haz Manifest · BOL. Generator from Job; TSDF locked by first approval; Transporter 1 required, 2 optional; **delivery mode lives here** (Direct / LTL → TSDF / LTL → hub); MTN entered (check-digit validated); signature dates; QC1 / QC2 status. |
| **Container** | One physical container | — | Generated from Shipping Document lines; edited individually for actual weight. Pallet = Carrier container with `contents_type` + `contents_count` (C-lite, no child rows). Cost/price snapshot. |
| **Invoice** | Billing record for a Job | Lines (snapshotted from waste + service lines at actuals) | Status: Draft → Issued → Entered in QB (stores QB invoice #) → Paid. Output is a PDF transcribed into QuickBooks. |
| **Project** | Optional parent for multi-day work | — | Phase 2 |

### Infrastructure (phase 1, invisible)

- **Users + roles:** Admin · Cost Editor · Sales · Chemist · Ops · Billing · QC Reviewer. Google Workspace sign-in only.
- **Audit log** on every create/update/delete: who, when, before/after.
- **Sequences:** account # (5-digit), job #, lab pack #, invoice #, container #.
- **Global search** across Accounts, Contacts, Regulated Entities, Jobs, Profiles, Shipping Documents.
- **File storage** (GCS): attachments, uploaded signed documents, generated PDFs.

---

## 2. Workflows

### Prospect → Customer

`prospect_stage`: Unidentified → Decision Maker Identified → Opportunity Identified → Qualified | Disqualified (reason required).

- Creating an Opportunity on a prospect Account sets stage = Opportunity Identified; moving the Opportunity to Technical Review or later sets Qualified.
- Opportunity Closed Won on a prospect prompts conversion: type → Customer, customer-required fields enforced, main contact gets the Main role on account and generator site.
- Knowsys CSV/XLSX import creates prospect Accounts (name + source only required).

### Activities

Status set by type:

| Type | Statuses |
|---|---|
| Call | Scheduled → Completed · No Answer · Voicemail |
| Site Visit | Scheduled → Contact Made · No Contact Made · Decision Maker Identified |
| Email | Sent (Opened later, if open tracking is ever added) |
| Meeting | Scheduled → Completed · No Show · Cancelled |

- Completing a Site Visit with outcome Decision Maker Identified advances the
  Account's `prospect_stage` to Decision Maker Identified if it is lower. The
  activity drives the stage; nobody updates both by hand.
- Logging on the go: a quick "log activity" action on Account, Contact and
  Opportunity pages, sized for a phone. Tapping a contact's phone number opens
  the dialer **and** creates a Scheduled Call activity; the page asks for the
  outcome on return. A web app cannot detect that a call happened, so this is
  the honest version of "calls initiated in-app get logged automatically".
- Emails sent from the app log an Email activity automatically once email
  integration lands (phase 2). Until then, Email activities are logged by hand.
- Tags are an admin-managed list, not free text, so reports can group on them.

### Cadences

- Enrolling an account or contact creates the step-1 Activity on its due date.
  Completing a step's Activity creates the next one. Exiting (closed won, do not
  contact, etc.) cancels the open Activity and records the reason.
- A **Today** view lists the owner's due and overdue activities across all
  enrollments, with the step's template or script inline.
- Phase 1: tracking plus templates/scripts. Phase 2: Email steps send
  automatically; exit rules fire on Opportunity stage changes.

### Opportunity ↔ Job

- A Job may be created with or without an Opportunity. Repeat customers go straight to a Job.
- When linked, the Job's pre-close stage is **read from** the Opportunity (Estimate Created, Secondary Review). No second stage field.
- Closed Lost → Job status Cancelled; hidden from working lists; kept for re-quoting. No purge.
- Closed Won → Job enters its operational pipeline; revenue goes to the projection report (phase 2).

### Job stages by type

| Type | Stages |
|---|---|
| Waste-hauling (LTL, Direct, Bulk, Transportation Only) | Estimate → Profile Review → Profiling → Profiles Submitted → **Price Review** (gate) → Ready to Schedule → Scheduled → Service Complete → Ready to Bill → Billed |
| Field Service · Training · Sampling | Estimate → Ready to Schedule → Scheduled → Service Complete → Ready to Bill → Billed |

- Profile Review → Profiling fires when the first profile leaves Draft; → Profiles Submitted when all profiles on the job are Submitted or Approved.
- Service Complete requires QC1 on every shipping document (or final-manifest review for direct loads).
- Ready to Bill is held when the Account has `shipping_documents_required` and the final signed document isn't uploaded.
- Credit Hold on the Account blocks any stage past Estimate.

### The price-review gate (the chicken-and-egg fix)

1. At Estimate, a Waste Line prices from **Waste Category + billing unit** (plus an assumed delivery mode, defaulted from the likely destination). No approval exists yet.
2. When a TSDF Approval is linked to the line, the engine recomputes.
3. If the new price differs from the snapshot beyond a tolerance (constant, cost-editor adjustable), the Job cannot pass Price Review until a user with pricing rights accepts the new price or re-confirms the old one. The choice and reason are audited.
4. When the Shipping Document is created, the line's delivery mode becomes actual and freight/handling reprice at cost; a margin warning fires if price − cost < floor.

### Shipping documents → containers → QC

- A Shipping Document line "12 × 55GDM" generates 12 Container rows with estimated weights.
- QC1 (yard reconciliation): count, type, actual weights vs. document → QC1 status.
- QC2 (final review): handling code vs. TSDF-entered, signatures, discrepancy box → locks the document. Reviewer ≠ preparer, enforced.
- Print flags per line/document: omit No., Total Qty, manifest # (shipping docs) or line #, container #, manifest # (labels) to produce accumulation labels. Also a "replacement accumulation label" toggle.

### Invoicing

- "Jobs Ready to Bill" list = Service Complete + no invoice + shipping-document hold cleared.
- Invoice generated from the Job at actuals; lines snapshotted; PDF rendered; Michaela transcribes into QB and records the QB invoice #.
- Lines on a `contract_pricing_expected` account that resolved to a default rate carry a warning on the Invoice (see §3).

---

## 3. Pricing

**Cost** (on Waste Line save, and on Reprice):

```
disposal = unit rate (approval exception cost if present) + vendor fees (Account rows)
minimum  = vendor minimum, same fee treatment
handling = $35 × Container Type multiplier when delivery mode is LTL (bulk = 0)
freight  = destination's 3rd-party LTL rate when delivery = LTL via hub (+ transport-side fees)
```

**Price — most specific wins, same billing unit only, never cross units:**

1. Approval Pricing Exception (fixed price or margin, with reason)
2. Account Contract Price (category × unit)
3. List = (disposal + fees) ÷ (1 − tier margin), plus handling + freight at cost
4. Nothing resolves → line **blocked**

**Tiers:** A / B / C are margin tiers on the Account. There is no "Custom" tier.

**`contract_pricing_expected` (the wish list's "Custom" pricebook):** a flag, not a tier. It never changes resolution. When set and a line resolves at step 3 (list price, no contract match), the line is flagged "default rate on contract account" on the Job and Invoice. Warning, not block — one-off items on contract customers are normal.

**Acceptance test:** reproduce `_Red_Arc_Disposal_Price_Calculator.xlsx` to the cent for US Ecology Tulsa, Clean Harbors Deer Park, Tradebe, Chem Rec, Itasca (per vendor-cost-scope v0 §3).

---

## 4. Documents and printing

| Document | Rendering | Printer |
|---|---|---|
| HW Manifest 8700-22 | Overprint: variable data only, positioned onto the pre-printed form | Dot-matrix, from the browser (Ctrl+P, "Actual size") |
| Non-Haz Manifest | Same engine, same field map, different pre-printed form | Dot-matrix |
| LDR | Overprint or full page per template (TBD when template arrives) | Dot-matrix or laser |
| BOL | Full-page PDF from template | Laser |
| Labels (accumulation / shipping) | Full-page PDF | Label/laser |
| Estimate, Customer Price List, Invoice | Full-page PDF (HTML → PDF) | Laser |

- Calibration page + saved X/Y offset per printer, baked into each overprint PDF.
- The raw ESC/P engine in `app/printing/` stays as a fallback if browser printing misaligns or prints light on carbons.
- Templates: Zak supplies PDFs for manifest, non-haz manifest, LDR, BOL, labels, estimate, price list, invoice.

---

## 5. Code structure

```
redarc/
  core/       users, roles, audit log, sequences, global search, file storage
  crm/        accounts, contacts, regulated entities, opportunities, activities,
              cadences, templates, knowsys import
  library/    reference tables + seed loaders
  waste/      profiles, tsdf approvals, lab pack inventories
  pricing/    container types, vendor price lines, service items, waste categories, engine
  jobs/       jobs, waste lines, service lines, stage machine, price-review gate, projects
  shipping/   shipping documents, lines, containers, QC1/QC2
  billing/    invoices, ready-to-bill
  documents/  PDF rendering: overprint engine + full-page templates
  assist/     Claude helpers (phase 2)
```

Django LTS · Postgres · HTMX · Google sign-in · Cloud Run + Cloud SQL + GCS · GitHub Actions → staging → production (manual approval).

---

## 6. Build order

Each slice is usable before the next starts.

| # | Slice | Done when |
|---|---|---|
| 1 | **Foundation** — auth, roles, audit, sequences, Accounts / Contacts / Regulated Entities, Activities (all four types, quick-log on mobile), libraries seeded, Zoho data migrated, global search | Staff can look up any account/site/contact and log a call or visit against it; Zoho CRM modules can be retired |
| 2 | **Cost + pricing** — Container Types, Vendor Price Lines, Vendor Fees, LTL Rates, Contract Prices, Service Items, engine | Calculator acceptance test passes to the cent |
| 3 | **Profiles, approvals, lab packs** — plus lab-pack-sorter import | A chemist can take a stream from Draft to Approved and build a lab pack |
| 4 | **Jobs + estimates** — all job types, stage machine, waste/service lines, estimate PDF, price-review gate | A rep can quote and a job can reach Ready to Schedule |
| 5 | **Shipping documents + containers** — HW manifest, non-haz manifest, BOL, LDR, labels, calibration, QC1/QC2 | A job can be shipped, printed, reconciled and locked |
| 6 | **Invoices** — ready-to-bill list, invoice PDF, shipping-docs hold, contract-rate warnings | Michaela bills from the app |
| 7 | **Sales pipeline** — prospect stages, opportunities, cadences + templates, Today view, Knowsys import, mobile views | Sales works from a phone |

**Phase 2+:** email integration (send from the app, auto-log Email activities, shared email threads on records, shipping-document send logic per RE spec §3), cadence email automation, Claude assists (account form fill, SDS → profile, code suggestions), QuickBooks sync, RCRAInfo e-Manifest, Projects, annual waste summary, revenue projection, 10-day yard inventory, outbound loads, commission reporting.

---

## 7. Decisions log

| Date | Decision |
|---|---|
| 2026-10-08 | Prospect is an Account type with a stage field, not a separate table |
| 2026-10-08 | Jobs may exist without an Opportunity |
| 2026-10-08 | "Custom" pricebook = `contract_pricing_expected` flag; warns on default rates, never a margin tier |
| 2026-10-08 | Lost jobs: Cancelled and hidden, never purged |
| 2026-10-08 | Build ops first (slices 1–6), sales pipeline last |
| 2026-10-08 | Non-haz manifests and BOLs are phase 1 shipping document types |
| 2026-10-08 | All seven job types in phase 1; non-transport types use the short stage set |
| 2026-10-08 | Delivery mode lives on the Shipping Document, not the Job (wish list over v2) |
| 2026-10-08 | Containers generate from Shipping Document lines, not Job waste lines (wish list over v2) |
| 2026-10-08 | Browser printing of generated PDFs replaces the local print agent; ESC/P engine kept as fallback |
| 2026-10-08 | Invoices are a module with PDF output transcribed into QB; QB API sync is phase 2 |
| 2026-10-10 | Activities: one table with type-specific statuses; in slice 1 because ops logs calls and visits too |
| 2026-10-10 | Site Visit outcome "Decision Maker Identified" advances prospect stage; no manual double entry |
| 2026-10-10 | Cadences + Templates in slice 7 (tracking and scripts); automated email steps phase 2 |

---

## 8. Open items

- [ ] Waste category / treatment list and vendor process codes (Zak) — gates slices 2 and 4
- [ ] Margin-warning floor value
- [ ] Price-review tolerance value
- [ ] Market picklist values
- [ ] PDF templates: manifest, non-haz manifest, LDR, BOL, labels, estimate, price list, invoice
- [ ] Printer models + spare blank forms for calibration
- [ ] User list with roles; backup QC reviewer per role
- [ ] 3–5 real past jobs as end-to-end test cases (lab pack, bulk, LTL via hub, one with a pricing exception, one field service)
- [ ] Exemption and exclusion lists
- [ ] Activity tag list; Meeting statuses (proposed: Completed / No Show / Cancelled) to confirm
- [ ] First cadence(s) to seed: steps, offsets, scripts
- [ ] Updated waste type / treatment mapping in the project folder — Zak reviewing; do not use until released
- [ ] Environment setup checklist (Google Cloud, DNS, GitHub, Claude environment) — in chat 2026-10-08, to be moved here
