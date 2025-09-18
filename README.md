# Inclusive Design Platform (idp)

Monorepo scaffold for the Inclusive Design Platform. This initial commit provides dev tooling only — services are placeholders with no framework logic yet.

## Services

- api (Python placeholder)
- worker (Python placeholder)
- web (Node placeholder)
- postgres
- redis
- minio
- docs

Service names match `docker-compose.yml`.

## Quickstart

1. Prerequisites
   - Docker and Docker Compose
   - Make
   - Python 3.11+ (for local pre-commit)

2. Setup environment
   - Copy env file: `cp .env.example .env`

3. Start dev stack
   - `make dev`
   - This builds and starts the containers: `api`, `worker`, `web`, `postgres`, `redis`, `minio`, `docs`.

4. Inspect
   - `make ps` to see status
   - `make logs` for aggregated logs
   - `make down` to stop and remove containers/volumes

![CI](https://github.com/${GITHUB_REPOSITORY}/actions/workflows/ci.yml/badge.svg)

## Tooling

- Pre-commit: Black, isort, Ruff (Python); Prettier + ESLint (web)
- CI: GitHub Actions runs pre-commit on push/PR

Install hooks locally:

```bash
pip install pre-commit
make pre-commit-install
```

Run format/lint locally:

```bash
make fmt
make lint
```

## Repo Layout

```
api/            # Python API placeholder
worker/         # Python worker placeholder
web/            # Web placeholder (Node)
docs/           # Docs placeholder
.github/        # CI
```

## Plan

1) Core Product Pillars

• Anthropometrics & Abilities Data
• Standards & Guidelines Rules Engine
• Simulation Services (reach, strength, visual, auditory, cognition)
• Design Evaluation & Inclusivity Index
• Parametric Adaptive Components Library
• CAD/PLM Integrations and API
• Study/Project Management, Reporting & Evidence

2) User Roles & Permissions

• Superadmin
Full platform control, data governance, tenant provisioning, standards publication.

• Organization Admin
Manages members, projects, datasets, rules packs, SSO, integrations.

• Designer (CAD user)
Creates projects, uploads models/parametrics, runs evaluations, uses component library.

• Researcher (Ergonomics/HCI)
Curates datasets, builds rule sets, defines simulations and thresholds, validates studies.

• Reviewer/Stakeholder
Read-only access to dashboards, reports, and audit trails.

• Contributor (Community Library)
Submits adaptive components or guidelines proposals for moderation.

Role-based access controls (RBAC) must be attribute-aware (project, dataset, jurisdiction).

3) Data Model (Key Entities)

• Organization
name, domain, SSO config, data residency, retention policies.

• User
profile, role(s), org memberships, audit log linkage.

• Project
title, description, sector (mobility, consumer electronics…), target demographic profiles, jurisdictions, visibility, linked standards versions.

• Design Artifact
versioned uploads: CAD file references, neutral parametric spec (JSON), key dimensions, materials, controls (buttons, handles), force requirements, visual/graphic attributes.

• Anthropometric Dataset
metadata (source, year, region, N, percentiles available), body dimensions (stature, sitting height, reach, hand span, finger lengths…), distribution parameters, stratification (age, sex, region, impairment classes).

• Ability Profiles
grip strength distributions, torque capability, pinch, dexterity, mobility ranges, vision (acuity, color perception), hearing (thresholds), cognitive load profiles. Mapped to population segments.

• Standards & Guidelines
normative references (ISO, EN, ADA, WCAG, IEC), machine-readable rules (condition → threshold → outcome), scope (product category), jurisdiction, versioning, evidence links.

• Simulation Scenario
pose model (standing/sitting, left/right hand), environment (counter height, lighting), device orientation, user profile mix, constraints.

• Evaluation Run
inputs (artifact version, rule packs, anthropometrics scope), results per rule/simulation, Inclusivity Index, flags, recommendations, diffs vs previous run.

• Adaptive Component
parametric model, constraints, capability ranges, documentation, usage metrics, versions, license.

• Report
frozen snapshot of evaluation run, charts, narrative, standard coverage, export formats.

• Audit Event
who, what, when, before/after, signature (optional), integrity hash.

4) Services & Engines

Anthropometrics Service
• Stores heterogeneous datasets with metadata, units, normalization.
• Interpolates percentiles; supports stratification queries (e.g., “female, 65–80, Portugal”).
• Provides reach vectors and posture models for forward kinematics.

Abilities Service
• Stores force/strength distributions (by grip type), dexterity, joint ROM, visual and auditory profiles.
• Maps to tasks: twist knob, push button, lift handle, read label at X lux.

Standards/Rules Engine
• DSL or JSON/YAML rules format: condition, variables, thresholds, references, remediation hints.
• Composable “Rule Packs” by sector, jurisdiction, product class.
• Deterministic evaluation, explainable outcomes (evidence → rule → result).
• Versioning and deprecation with project pinning.

Simulation Engine
• Geometry intake: CAD-neutral (STEP/IGES), glTF for viz, and parametric JSON from plugins.
• Reach envelopes: static and posture-aware; collision tests; min/max reach by percentile.
• Strength checks: force/torque feasibility based on profile distributions and task orientation.
• Visual simulations: color-vision deficiency filters, contrast ratio checks, font size at distance, glare models (basic at MVP, HDR later).
• Auditory: SPL audibility thresholds in simple environments (MVP).
• Output: pass/fail bands, probability-of-success estimates per population segment.

Inclusivity Index Engine
• Weighted aggregation of simulation and rules outcomes.
• Segment-aware scoring (e.g., 5th–95th percentile coverage), uncertainty bounds, scenario-weighted results.
• Transparency: breakdown by task, user segment, scenario.

Recommendation Engine
• Deterministic (rule-based) mitigations plus heuristic suggestions tied to component library.
• “What-if” sliders: live recompute when dimensions/forces change.

Parametric Components Service
• Stores parameter schema and constraints.
• Validates claimed capability envelope (e.g., “usable down to 10th percentile grip strength”).
• One-click “swap-in” from CAD plugin with parameter mapping.

Reporting & Evidence Service
• Generates signed PDFs/HTML reports with standards mapping.
• Comparison reports across versions and scenarios.
• Data export (CSV/JSON) for research.

5) Interfaces

Web App (Design Console)
• Project home with Inclusivity Index trend, flags, tasks.
• Model viewer (WebGL) with reach envelopes, heatmaps, collision overlays.
• Rule results pane: evidence, standard citation, remediation.
• What-if panel: change dimensions/forces and recompute.
• Dataset selector (population slices), scenario builder, component swapper.
• Report builder with template presets (internal review, certification prep, research paper appendix).

CAD Plugins (MVP: FreeCAD; later: Fusion/Rhino/Onshape)
• Push parametric key dimensions and control metadata.
• Pull evaluation flags inline (tooltips on features).
• Insert adaptive components with mapped parameters.
• Local caching for offline work; conflict resolution.

API (GraphQL + REST)
• Auth: OAuth2/OIDC, PATs for CI, fine-grained scopes.
• Endpoints for projects, artifacts, runs, datasets, components, reports.
• Webhooks for run completion, threshold breaches, governance events.

CLI (for pipelines)
• Batch evaluations in CI (e.g., on PR), artifact diffs, report exports.

6) Data Pipelines & Integrations

• Importers: anthropometrics (CAESAR-like), abilities (NHANES-like), standards (curated JSON).
• ETL validation: units, distributions, metadata completeness, provenance.
• PLM/Issue tracking: Jira/GitLab/GitHub issues from failed checks.
• SSO/IdP: SAML/OIDC (Okta, Azure AD).
• Storage: object store for models (S3-compatible), relational DB for metadata, vector tiles for heavy viz later if needed.

7) AI Layer (Optional but Future-Proofed)

• NLQ: “Can a seated 5th percentile user press this button?” maps to deterministic checks.
• Pattern mining: correlate flags across projects to suggest high-impact fixes.
• LLM narrative drafting for reports, constrained by deterministic results and citations.
• Strict guardrails: AI never overrides rules; it explains and drafts.

8) Non-Functional Requirements

Security & Privacy
• Data residency per org; encryption at rest and in transit.
• PII-minimal design; datasets are aggregate/statistical.
• Detailed audit logging; tamper-evident report signing.
• Role/attribute-based authorization; scoped API tokens.
• Vulnerability scanning, dependency SBOM, pen tests.

Performance & Scale
• Async job queue for simulations; autoscaling workers.
• Model pre-processing and caching of reach volumes and envelopes.
• Target: typical evaluation < 30s for medium models; progressive results stream.

Reliability
• Blue/green deployments; rolling updates for rules packs.
• Backups, disaster recovery, RPO/RTO clear targets.

Compliance
• Map rules to ISO/EN/ADA/WCAG citations; version pinning.
• Accessibility of the platform itself (WCAG 2.2 AA).
• GDPR compliance: DSR endpoints, retention policies.

Observability
• Structured logs, traces, metrics; per-tenant dashboards.
• Usage analytics for components and rule packs.

9) MVP Scope (12–16 weeks realistic)

• Projects, users, RBAC, organizations.
• Upload CAD + parametric spec capture via FreeCAD plugin.
• Anthropometrics v1: stature, arm length, hand span, sitting/standing reach (5th–95th).
• Abilities v1: simple grip and push force distributions.
• Rules Engine v1: selectable pack with 20–30 codified checks (reach heights, control spacing, contrast ratio basic).
• Simulation v1: 3D reach envelopes, collision checks, simple force feasibility.
• Inclusivity Index v1: transparent weighted scoring.
• Reports v1: signed PDF/HTML with citations and diffs.
• Component Library v1: 10 adaptive components (handles, knobs, buttons) with parameter schemas.
• API v1 + Webhooks; simple CLI.
• Basic governance: audit logs, dataset provenance.

10) Phase 2 (next 6–9 months)

• Visual simulations: color vision deficiency filters and contrast validation in 3D context.
• Auditory checks and simple psychoacoustic models.
• Cognitive load heuristics (learnability, error-proneness) via structured checklists mapped to standards.
• Multi-jurisdiction rule packs and rule composer UI.
• Organization-level analytics and cohort benchmarking.
• PLM integrations (Jira, GitLab), CI policies (“block merge on critical exclusion”).
• Community submission flow for components with moderation.

11) Phase 3 (research/industry scale)

• Posture optimization, dynamic reach under motion.
• Strength/biomechanics models per joint; task-specific torque envelopes.
• IoT/field feedback loop: real prototype measurements → model calibration.
• Probabilistic compliance (Bayesian): credible intervals for index.
• AI-assisted rule authoring with provenance checks.

12) Measurement & Validation

• Technical KPIs: evaluation latency, cache hit rate, rule coverage, false positive/negative vs expert reviews.
• Design KPIs: % improvement in Inclusivity Index after recommendations, number of flagged issues resolved, time-to-compliance.
• Research KPIs: inter-rater reliability of rules; external benchmark studies; reproducibility artifacts.

13) Tech Stack (suggested)

• Backend: Python (FastAPI) or TypeScript (NestJS); Postgres; Redis; S3-compatible storage; Celery/Sidekiq equivalent for jobs.
• Frontend: React + WebGL (Three.js); accessibility-first UI.
• CAD: FreeCAD plugin (Python) for MVP; gRPC/REST bridge.
• Infra: Kubernetes, Terraform; OIDC SSO; OpenTelemetry.

14) Documentation & Governance

• Public docs site with versioned rule packs, change logs, deprecation notices.
• Data catalogue for datasets (source, quality, limitations).
• “Assurance case” templates for audits and certification pathways.
• Ethics statement: limitations, biases in datasets, responsible use.


## License

MIT
