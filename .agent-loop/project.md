# Project Memory

Created: 2026-07-31
Updated: 2026-07-31
Status: active
Memory Mode: simple

## Project Summary

Purpose: Take-home interview exercise — make a synthetic clinical-record corpus semantically searchable end to end (indexing + practice-isolated vector search API + search UI).
Primary users: interview reviewer; local demo users (3 mock practices).
Current maturity: provided scaffold is green; candidate-owned areas (schema, indexing, search API, search UI, acceptance tests) are stubs.
Guidance Language: English (repo docs and reviewer are English; conversation with the human is Chinese).
Language Evidence: README.md, docs/TAKE_HOME_DESIGN.md, all in-repo docs are English.

## Project Memory Index

Mode: simple

- Decisions: none
- Project Skills: none
- Bug Inventory: none

This file is the main long-term project memory body.

Memory Mode Evidence:
- Small monorepo, 3 boundaries (web / api / embedding+db), single test strategy document fits in this file.

## Product Context

Product Positioning: retrieval-only clinical record search; must never generate diagnoses, infer unrecorded conditions, or present similarity as clinical confidence.
Target Users: clinicians searching their own practice's records with natural language.
Core Workflows: index source documents -> natural-language query -> ranked patient-level results with supporting passage -> navigate to patient detail.
Business Rules:
- Practice isolation is enforced server-side; the search request must not accept a client-selected practice identifier.
- Every result must cite an existing source document and a supporting excerpt; no full documents when an excerpt suffices.
- Patient-level results: each patient appears at most once in the primary list.
- Indexing must be idempotent and reflect source changes without a full manual reset.
Cross-Feature Product Constraints: no logging of document bodies, excerpts, patient names, or embedding vectors; no external services for records.
Out of Scope Across Product: production auth, hosted embedding providers, diagnosis generation, reranking models, negation/history perfection, visual redesign.

## Tech Stack

- Runtime: Docker Compose v2 (Python, Node, pnpm, ONNX model all inside images)
- Frameworks: Next.js 16 (App Router, Tailwind v4), FastAPI, PostgreSQL 18 + pgvector, ONNX MiniLM embedding service (384-dim)
- Package manager: pnpm (web), pip/pyproject inside api image
- Data/storage: PostgreSQL with pgvector; committed CSV seed data (3 practices, 715 patients, 2,400 documents)
- Test tools: pytest (api, incl. deterministic embedding stub), vitest/pnpm test (web), `make smoke`

## Architecture Profile

Project Shape: fullstack
Language Adapter: python + node-ts
Framework Adapter: fastapi + nextjs (other)
DDD Intensity: light
Layout Status: existing reality
Scaffold Rule:
- Governance scaffold is relatively stable.
- Code layout is a stack-adapted recommendation, not a mandate.
- Existing project structure is not changed without explicit human approval.
Evidence: README.md Layout section; apps/web, services/api, services/embedding, database/.
Confidence: high

## Project Principles

- Follow existing project conventions; keep the implementation proportionate to the exercise (docs/TAKE_HOME_DESIGN.md §8).
- Respect the embedding service contract: 384-dim, max 256 tokens, 64 texts/request, 8,000 chars/text, blank input rejected.
- Do not modify `database/migrations/0001_base_schema.sql` or `services/embedding/`; they are provided platform.

## Domain Language

- `practice`: tenant boundary; all search results are isolated to the authenticated user's current practice.
- `clinical_document`: source record; types: diagnostic_note, specialist_note, radiology_report, lab_report.
- `chunk`: searchable segment of a clinical document (schema is candidate-designed).
- `evidence`: the document + passage that explains why a patient matched.

## Development Rules

- TDD is default: RED, verify RED, GREEN, verify GREEN, refactor.
- Add new migration as `database/migrations/0002_*.sql`; never edit 0001.
- Candidate-owned areas: chunk/embedding schema, indexing workflow, `POST /api/clinical-search`, `/search` UI, acceptance tests.

## Testing Rules

- Acceptance placeholders ship as `xfail`; replace them with real deterministic tests.
- Tests must not require paid or uncontrolled external services; use the deterministic embedding stub for unit/acceptance, real container for `make test-integration`.

## Project Skills

Index: none
Active Bootstrap Skills:
- none
Active On-Demand Skills:
- none
Proposed / Disabled / Deprecated:
- none
Execution Rule: loading never authorizes execution; each invocation requires the Project Skill Execution Gate.

## Branch Strategy

Adoption Status: not-needed
Profile: not-applicable
Decline Reason: required when Adoption Status is declined | not-applicable
Main Branch: main
Standard Release Pattern: none — exercise is evaluated locally; human stated no code submission (no push/PR) is required.
Customer Release Pattern: none
Development Pattern: work directly in the local clone; no branch mutation authorized.
Release Immutability: none
Customer Isolation: none
Deletion Policy: none
Human Confirmed: 2026-07-31, human said "不用提交代码"
Evidence: conversation 2026-07-31.

Recording Rules:
- An unanswered recommendation is not `accepted`.
- Changing durable strategy requires Drift Check and a Human Gate.

## Current Work

Active Feature: .agent-loop/features/2026-07-31-semantic-search/ (all tasks done; close pending human confirmation)
Paused Features: none
Target Release Context: none
Next Suggested Action: Close Feature 2026-07-31-semantic-search after human confirmation; then human spot-check in the browser (`make dev`, /search) within the remaining 48h window.
Gate Mode: Feature Auto-Loop
Gate Mode Scope: Feature 2026-07-31-semantic-search, accepted stories US1..US4, tasks T001..T006
Gate Mode Stop Conditions: all six gate classes; scope/boundary change; failed verification after diagnosis; human lifecycle request
Feature Follow-up Lookback: 90 days
Current Memory Merge Report: none
Current Memory Merge Status: none
Current Memory Merge Blocker: none
Memory Conflict Pointer Rule: keep only an unresolved/material conflict report locator, status, and blocker here.
Recent Feature Flow-back Policy:
- For explicit Bug management, scan all Bug Index metadata for duplicate/reopen identity, then scan Feature metadata in the configured window.
- Flow back to the owning Feature only after the Bug Resolution Path and any Feature reopen/create gate are confirmed.

## Remote Entry

Mode: none
Remote Entry File: none
Remote Project Memory:
- Location: none
- Path:
- Status: none

Note: origin remote `https://github.com/medlink-global/interview` exists but is read-only context; no push/PR per human decision.

## Environment Map

Local Workspace:
- Path: /Users/wangheng/Workspace/interview
- Purpose: primary
- Evidence: git clone of the exercise repo
- Confidence: high

Execution Locus:
- Install/Build/Tests/Dev Server/Database: all inside Docker Compose (`make setup`, `make dev`, `make test`)
- Evidence: README.md Quick start; Makefile
- Confidence: high
- Known gap: Docker daemon was NOT running at scan time (2026-07-31 11:42 CST); human must start Docker Desktop before `make setup`.

Sync Model:
- Method: local-only
- Source of truth: local clone
- Stale risk: none

## Capabilities

- App shell, layout, navigation, design-system primitives: implemented (provided)
  - Evidence: apps/web/app/layout.tsx, components/ui/
  - Confidence: high
- Mock session with practice switcher: implemented (provided)
  - Evidence: apps/web/app/api/demo-session/route.ts
  - Confidence: high
- Patient detail route `/patients/[patientId]`: implemented (provided)
  - Evidence: apps/web/app/patients/[patientId]/page.tsx
  - Confidence: high
- FastAPI config, pool, error envelope, request logging, health: implemented (provided)
  - Evidence: services/api/app/
  - Confidence: high
- Migration runner, seed loader, smoke: implemented (provided)
  - Evidence: services/api/app/scripts/
  - Confidence: high
- Embedding service (ONNX MiniLM 384-dim) + typed client: implemented (provided, not part of assignment)
  - Evidence: services/embedding/, services/api/app/clients/
  - Confidence: high
- `/search` route: implemented (search experience, six states, Server Action)
  - Evidence: apps/web/app/search/page.tsx, apps/web/features/search/
  - Confidence: high
- Chunk/embedding storage schema: implemented (migration 0002: document_chunks + document_index_state)
  - Evidence: database/migrations/0002_document_chunks.sql, migrate re-run no-op
  - Confidence: high
- Indexing workflow (`make index`): implemented (idempotent, change detection, per-document failure tolerance, summary)
  - Evidence: services/api/app/features/indexing/, rerun writes zero chunks
  - Confidence: high
- `POST /api/clinical-search`: implemented (validated, practice-isolated vector retrieval, patient-level aggregation, evidence)
  - Evidence: services/api/app/features/search/, acceptance + integration tests
  - Confidence: high
- Acceptance tests: implemented (all 9 placeholders replaced; MT-06 added)
  - Evidence: services/api/tests/, 49 passed
  - Confidence: high

## Directory Map

- `apps/web/`:
  - Responsibility: Next.js 16 frontend (routes, design-system primitives, feature-local code)
  - Constraints: keep credentials and server-only config out of browser code; search feature goes in `apps/web/features/search/`
  - Useful commands: `make test-web`, `docker compose run --rm --no-deps web pnpm test`
  - Evidence: README.md Layout
  - Confidence: high
  - Guidance: root only
- `services/api/`:
  - Responsibility: FastAPI backend; `app/features/` holds health, session, patients, search*, indexing* (* = candidate)
  - Constraints: practice isolation enforced inside the trusted backend boundary
  - Useful commands: `make test-api`, `docker compose exec -T api pytest -q`
  - Evidence: services/api/app/features/
  - Confidence: high
  - Guidance: root only
- `services/embedding/`:
  - Responsibility: provided embedding service (ONNX MiniLM); contract: 384-dim, 256 tokens, 64/batch, 8000 chars, blank rejected
  - Constraints: do NOT modify; not part of the assignment
  - Evidence: services/embedding/README.md
  - Confidence: high
  - Guidance: root only
- `database/`:
  - Responsibility: init scripts, migrations (0001 provided; add 0002), seed generator + committed CSVs
  - Constraints: never edit `0001_base_schema.sql`; migrations run in filename order, transactional, recorded
  - Evidence: database/migrations/README.md
  - Confidence: high
  - Guidance: root only
- `docs/`:
  - Responsibility: TAKE_HOME_DESIGN.md (specification, human source requirement), DATASET.md
  - Constraints: human-owned; never modify
  - Confidence: high
  - Guidance: root only

## Directory Guidance

Root Guidance:
- `AGENTS.md`: created (2026-07-31)
- `CLAUDE.md`: created-pointer (2026-07-31)
- Sync Rule: `AGENTS.md` is maintained primary guidance; `CLAUDE.md` points to `AGENTS.md`.

Directory-Level Guidance:
- none proposed; boundaries are few and this is a 48h exercise — `not needed`.

Creation Rule:
- When creating a new long-lived boundary directory, propose a directory-level `AGENTS.md` and ask for human confirmation before writing it.

## Test Commands

- `make test`:
  - Verifies: backend (pytest) + frontend (pnpm test) suites
  - Evidence: README.md, Makefile
  - Confidence: high
- `make test-integration`:
  - Verifies: real embedding container path
  - Evidence: README.md
  - Confidence: high
- `make smoke`:
  - Verifies: database, seed data, real embedding call
  - Evidence: README.md
  - Confidence: high
- `make lint` / `make typecheck`:
  - Verifies: ruff, eslint, type checks
  - Evidence: README.md
  - Confidence: high

## E2E Environment

App Start:
- Command: `make setup && make seed && make dev`
- URL: web http://localhost:3000, API http://localhost:8000
- Evidence: README.md
- Confidence: high

Auth / Test Data:
- Test Account: mock demo users, one practice each; header dropdown switches identity
- Seed Command: `make seed` (deterministic, repeatable)
- Evidence: README.md Session and practice context
- Confidence: high

External Services:
- Mocked: embedding via deterministic stub in unit/acceptance tests
- Real: local embedding container only; no external network at run time
- Evidence: README.md, docs/TAKE_HOME_DESIGN.md §7
- Confidence: high

## Project Entry Scan

Last Scan: 2026-07-31

Read:
- Startup docs: README.md, docs/TAKE_HOME_DESIGN.md, docs/DATASET.md, PULL_REQUEST_TEMPLATE.md
- Manifests / scripts: Makefile, docker-compose.yml, .env.example, database/migrations/README.md
- CI / test configs: .github/workflows/ci.yml
- Boundary files: per-area READMEs (migrations, indexing, search api, search ui, acceptance tests)

Confidence:
- Project purpose: high
- Tech stack: high
- Capabilities: high
- Test commands: high
- Directory boundaries: high

## Project Entry Uncertainties

- Exact remaining time in the 48h window (repo access start time unknown):
  - Evidence: docs/TAKE_HOME_DESIGN.md §2 (48 consecutive hours from access)
  - Confidence: low
  - Recommended follow-up: human confirms the actual deadline; plan assumes completion well within window (~8–12 focused hours).
- Whether `.agent-loop/` and root guidance files should be committed if a PR is ever opened:
  - Evidence: human said no submission; .gitignore does not exclude .agent-loop
  - Confidence: low
  - Recommended follow-up: decide only if submission is revived.

## Known Constraints

- Repository access: 48 consecutive hours; expected effort 8–12 focused hours.
- No code submission (no push/PR) — human decision 2026-07-31.
- Docker daemon must be running for all setup/test commands.
- Embedding model (~90 MB) downloads at first image build only.
- Treat synthetic records as sensitive: no external services, no credentials committed, no content logging.

## Long-Term Decisions

- 2026-07-31: Requirement source is the in-repo human-owned `docs/TAKE_HOME_DESIGN.md`; no separate `.agent-loop/requirements/` copy is created to avoid duplicating a byte-stable repo file. Feature Spec Product Slice references its sections directly.
