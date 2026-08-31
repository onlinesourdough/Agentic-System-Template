# Agentic System Template

This repository is the neutral, instruction-owned seed for persistent Agentic
Systems. Read this file, `README.md`, and the primary skill at
`.agents/skills/agentic-system-template/SKILL.md`.

## Canonical model

AIOS has three first-class concepts: Space, System, and Project. Templates and
Skills support those concepts; they are not additional AIOS types.

Use a Skill when the reusable value is an instruction or method without
independent operational responsibility. Use a System when a reusable capability
must remain independently operable and own several responsibilities across
runs and outcomes.

## Concrete System ownership

The concrete System owns its domain responsibilities, operations, owner-local
workspace truth, evidence and proof, evaluation criteria, and failure/recovery
behavior. Establish only what those responsibilities actually require. Do not
impose a universal directory layout, ledger, schema, runtime, or audit rubric.

An adopted System remains standalone. It does not import this repository,
depend on an AIOS runtime, or receive later template overwrites.

## Agent routes

The primary skill establishes or maintains one concrete System. `audit-system`
is the separate read-only route for explicit accumulated-state inspection.
Each repository-local skill directory contains only its `SKILL.md` entrypoint;
cross-project and Global Skills remain harness- or plugin-installed elsewhere.

This seed contains no generic engine, demo state, fixtures, schemas, or runtime.
Do not add replacement scaffolding or mutate downstream Systems from here.
