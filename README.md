![Agentic System Template banner](assets/branding/system-banner.png)

# Agentic System Template

<a href="assets/branding/system-icon.png"><img src="assets/branding/system-icon.png" alt="Agentic System Template icon" width="32" height="32"></a>

Agentic System Template is a small, instruction-owned seed for persistent
Agentic Systems. It explains the ownership and operating boundaries without
shipping a generic implementation that every concrete System would inherit.

## When a System is justified

AIOS has three first-class concepts: Space, System, and Project. Templates and
Skills are supporting constructs.

Use a Skill when the reusable value is an instruction or method with clear
inputs, proof, and stop conditions but no independent operational
responsibility. Use a System when a reusable capability must remain
independently operable across runs and outcomes and materially owns several
responsibilities as one cohesive capability.

## What the concrete System owns

Establish only the surfaces required by the actual capability:

- its domain responsibilities and repeatable operations;
- the owner-local workspace truth needed to continue operating;
- evidence and proof for consequential outputs or checkpoints;
- System-local evaluation criteria tied to observable requirements;
- retained failure evidence and an explicit correction/recovery path when
  failures matter to future operation; and
- read-only accumulated-state and currentness criteria where drift matters.

Those needs do not imply a universal workspace layout, ledger, schema,
database, runtime, or audit rubric. The owning System chooses the smallest
durable form that makes its own work operable and inspectable.

## Operating decisions and proof

Each concrete System owns its material decisions, operational documentation,
proof, and recovery in the source-of-truth records it chooses. Those records
retain decision context, rationale, consequences, and supersession history when
the decision changes; the template prescribes neither an ADR format nor a
directory.

The [primary System method](.agents/skills/agentic-system-template/SKILL.md)
establishes domain responsibilities, operating truth and specialist proof.
Substantive Spec, Build, Review and authorized Ship use the installed AIOS plugin
as routed by [AGENTS.md](AGENTS.md). Narrow edits need only affected context and
proof. Requested repository audits use Review; local domain audit methods are added only when the concrete System needs them.

## Instruction surface

```text
AGENTS.md
README.md
.agents/skills/agentic-system-template/SKILL.md
```

Direct System tasks continue in their current session. The seed carries no
copied generic lifecycle or tracking methods and requires no AIOS runtime.

## Adoption and ownership

A concrete System explicitly adopts the useful boundary, then owns its skills,
state, criteria, evidence, and evolution. This template does not become a
dependency, synchronize downstream copies, or overwrite owner-local behavior
later. Cross-project and Global Skills stay outside the repository in the
harness or plugin that provides them.

Each maintained specialist skill has a quoted SemVer in YAML `metadata.version`,
starting at `"1.0.0"`. Bump only the skill whose contract changes: patch for
compatible corrections, minor for compatible capabilities, major for breaking
invocation or operating-contract changes. Skill versions are independent of
System and package versions. Create skills only for actual responsibilities.

## Instruction maintenance evidence

The 2026-09-12 instruction audit used OpenAI's
[Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
(2026-09-11): precise triggers, contextual reads, proportionate checks and
completion within existing authority. These are model-neutral authoring choices;
static validation does not establish model behavior.

For skill authoring or instruction-link changes, run the seed-only structural
check with Ruby's standard YAML parser (no installed gems required):

```sh
ruby tests/validate-system-template.rb
```

It checks the skill inventory, frontmatter, quoted SemVer and local links;
operating-contract changes also need representative domain proof.
