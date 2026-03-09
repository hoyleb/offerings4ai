---

# Agents.md

Agent: codex-plus (gpt-5.3-codex + gpt-5.1-mini edition)
Version: v05-Mar-2026
Autonomous Mode Enabled

---

# 💰 Cost Optimization & Performance

Status: Optimized via Prompt Caching (Azure East US)

Rules:

* Do NOT modify static context (System Prompts, Core Rules, Project Specs).
* Always append new task-specific data at the end.
* Modifying the prefix invalidates cache for the entire team.
* Prefer smallest sufficient model for routing, validation, or parsing logic.
* Escalate to heavier reasoning models only when complexity requires it.

---

# 🚀 Autonomous Execution Policy

This repository operates in **Autonomous Development Mode**.

Core Principle:

> Try first. Ask last.

Agents must NOT request permission for:

* Running builds
* Running tests
* Linting
* Formatting
* Docker compose
* Opening PRs
* Pushing commits
* Retrying transient failures
* Running E2E
* Using dry-run modes

If there is exactly one reasonable next action — execute it.

---

# 🔁 Task Continuity & Backlog Discipline (CRITICAL)

Default mode: **Single Active Task**

Only one task may be active at a time.

## Active Task Declaration (MANDATORY)

At task start, report:

Active Task:

* Short name
* Goal (1 sentence)
* Branch name

If mid-task and new instruction arrives, report:

* Current Active Task
* Approximate completion %
* Classification of new instruction

---

## Handling New Incoming Instructions

Classify new instructions as:

A) Clarification
→ Continue current task with refinement.

B) Modification
→ Adjust plan and continue.

C) New Independent Task
→ Append to TODO.md as backlog item.
→ Continue current task.

Do NOT silently context switch.

Switching tasks requires explicit instruction:

* “Abort current task”
* “Switch to backlog item: <name>”
* “Prioritize new task immediately”

---

## Backlog Contract (Persistent Memory)

All independent tasks must be appended to:

`TODO.md`

Format:

```id="ks9x4p"
## Backlog Item
Date:
Source:
Short Name:
Description:
Status: queued
```

Rules:

* Never overwrite existing backlog.
* Never store backlog only in model memory.
* Never drop user instructions.
* Backlog must persist across sessions.

---

## Task Switching Protocol (Explicit Only)

When switching tasks:

1. Commit or stash current work.
2. Ensure clean working tree.
3. Update TODO.md:

   * previous task → paused
   * new task → active
4. Declare new Active Task.

No silent switching.

---

## Half-Finished Work Prevention Rule

A task is not complete unless:

* Tests exist and pass
* Documentation updated if needed
* No TODO markers remain
* No commented-out code fragments
* No partial refactors
* Branch meets ready-to-merge criteria

If incomplete, task remains active.

---

# 🧠 Git & Worktree Lifecycle Contract (CRITICAL)

Default:

* Use primary working tree.
* Do NOT create additional worktrees unless required.

Worktrees MAY be created only for:

* Parallel long-running tasks
* Explicit isolation request

Before creating:

* Run `git worktree list`
* Reuse existing codex worktree if possible

After completion:

* Commit or discard changes
* Remove unused worktrees

  * `git worktree remove <path>`
  * `git worktree prune`

Zombie worktrees are a bug.

---

# 🧹 Dirty Worktree Resolution Policy

If `git status --porcelain` is dirty:

1. Identify origin of changes.
2. Choose ONE action:

   * Commit
   * Stash
   * Reset

Agents are allowed to run:

* git restore .
* git reset --hard HEAD
* git clean -fd
* git stash push -m "codex: auto-stash"

Never narrow scope silently due to dirty tree.

Resolve it.

---

# Git & Concurrency Policy

Never push to main.

Always:

* Create branch: codex/<short-task-name>
* Open PR
* Allow workflow to auto-merge

Ready-to-Merge Contract:

1. Clean git status
2. All checks passing
3. Commit message:
   chore: ready-to-merge

Never ask for merge approval.

---

# 🧪 Testing Contract

Goal: Smallest sufficient test proving correctness.

## Test Categories

Unit (fast)

* Pure logic
* Components
* Utilities

Integration (medium)

* API + DB
* Frontend + API mocking
* CLI flows

E2E (slow)

* Full docker compose
* Critical journeys only

## Required for Every PR

* Run relevant unit tests
* Run lint + typecheck
* Build must pass

Additionally required when modifying:

* docker-compose
* workflows
* auth
* publish logic
* API contracts

→ Run integration and E2E

---

## Common Commands

Backend:

* ruff format / check
* pytest -q
* python -m unittest (fallback)

Frontend:

* pnpm test || npm test
* lint
* typecheck
* build

Docker-first:

* docker compose up --build
* run E2E
* docker compose down -v

Containers must be shut down after E2E.

---

# 📝 Documentation Contract

Public behavior changes require documentation updates.

Update README or /docs if:

* Config changes
* New env variables
* CLI flags
* Behavioral changes

Python docstrings must include:

* Purpose
* Args
* Returns
* Raises (if meaningful)

TypeScript JSDoc required for:

* Exported functions
* Shared components

Comments must explain:

* Why
* Tradeoffs
* Edge cases

Do not comment obvious code.

---

# 🔐 Security Rules (GHES + GHAS)

Agents must never:

* Disable required status checks
* Bypass CodeQL
* Disable secret scanning
* Circumvent push protection
* Invent credentials

Fail loud:

* raise NotImplementedError(...)
* throw new Error("Not implemented")

Missing secrets:

* Run until failure boundary
* Report exact variable name
* Report where it must be placed
* Do not request permission before attempting

---

# 📌 Start-of-Task Invariant

Must report:

* Current branch
* Worktree count
* Dirty/clean status

Unknown state must be resolved before proceeding.

---

# 📌 End-of-Task Invariant

At completion:

* Exactly one active worktree (unless explicitly parallel)
* No untracked files
* No dangling worktrees
* Clean git status
* PR opened
* Ready-to-merge criteria met

---

# Final Behavioral Rule

If exactly one reasonable technical action exists: execute it.

If execution fails, report:

* What was attempted
* Exact command
* Exact failure
* Recommended next step

Do not ask for permission for normal development work.

--- 
