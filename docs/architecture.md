# Offering4AI Architecture

## Overview

Offering4AI is designed as a machine-readable idea protocol with a small, deployable MVP footprint.

### Components

- `frontend`: creator UI for auth, submission, and dashboard views
- `api`: FastAPI service for auth, idea creation, and dashboard queries
- `worker`: queue consumer that evaluates ideas and writes payouts
- `postgres`: system of record
- `redis`: background queue transport

## Request and Evaluation Flow

1. Creator registers and logs in.
2. Frontend relies on `HttpOnly` session cookies plus a CSRF token instead of storing auth state in `localStorage`.
3. Creator submits a structured idea to `POST /api/ideas`.
4. API validates payload, computes a content fingerprint, checks duplicate/similarity risk, and stores the idea.
5. API enqueues an evaluation job in Redis.
6. Worker dequeues the job and scores the idea.
7. Worker writes an evaluation record.
8. If accepted, worker writes a payout ledger entry and sets idea status to `paid`.
9. Frontend polls or refreshes dashboard state to show the result.

## Data Model

### User

- id
- email
- hashed_password
- full_name
- payout_address
- reputation_score
- created_at

### Idea

- id
- creator_id
- title
- category
- problem
- proposed_idea
- why_ai_benefits
- expected_reward_range
- license_type
- status
- score_total
- ownership_record
- content_fingerprint
- feedback
- similarity_score
- is_flagged_duplicate
- timestamps

### Evaluation

- idea_id
- evaluator_version
- novelty_score
- clarity_score
- utility_score
- leverage_score
- total_score
- decision
- rationale

### Payout

- idea_id
- gross_amount
- fee_amount
- net_amount
- currency
- provider
- transaction_reference
- status

## Evaluation Layer

### Default Local Evaluator

The MVP defaults to a deterministic evaluator so the system is stable in local tests and CI-like flows.

Rubric:
- novelty
- clarity
- utility
- strategic leverage

Acceptance threshold is controlled by `EVALUATION_THRESHOLD`.

### Optional OpenAI Evaluator

If you set:
- `EVALUATOR_PROVIDER=openai`
- `OPENAI_API_KEY=...`

then the worker switches to model-based evaluation using the configured `OPENAI_MODEL`.

## Anti-Abuse Controls in MVP

- content fingerprint uniqueness
- rough similarity scoring
- CSRF protection for browser sessions
- trusted host enforcement and production HTTPS-only behavior
- request throttling for auth, write, and public feed paths
- hourly submission rate limit
- structured schema enforcement

## Deployment Invariants

- run versioned migrations before API or worker startup
- keep browser auth on cookies rather than frontend token storage
- set explicit `PUBLIC_*`, `CORS_ALLOWED_ORIGINS`, and `TRUSTED_HOSTS` values in production

## Remaining Hardening Priorities

- add embedding-based duplicate detection
- add audit trails for prompt versions and payout decisions
- add durable notification layer for status updates
