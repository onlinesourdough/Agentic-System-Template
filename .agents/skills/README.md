# Repository-local skills

Repository-local skills use the flat direct-child path
`.agents/skills/<name>/SKILL.md`:

- `system-template` is the primary System entrypoint.
- `audit-system` is the separate, read-only accumulated-state audit.

Add a local skill only for a System- or domain-specific repeatable method or
eval. Cross-project and Global Skills remain harness- or plugin-installed
outside this repository.

After adoption, the concrete System owns its local skills. System Template is
only the seed and does not overwrite those skills later.
