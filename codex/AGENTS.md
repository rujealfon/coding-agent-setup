## Delegation

Apply this delegation policy in Codex sessions.

When acting as the primary agent, delegate independent work when it materially
improves speed or quality. Handle small tasks directly and keep orchestration,
scope decisions, integration, and final verification in the primary agent.

- Use `runner` for bounded read-only lookups, file discovery, and factual checks.
- Use `tracker` to trace behavior, dependencies, and likely causes across files
  without editing code.
- Use `fixer` to implement a defined change within assigned files and verify it.
- Use `inspector` for independent assessment of a specified diff for correctness,
  regressions, security issues, and missing validation.
- Use `default` for bounded mixed investigation and implementation when no
  specialist fits.
- Use each agent's configured model. Choose a supported reasoning effort for its
  task: low for simple lookups, medium for routine implementation, and high for
  complex investigation or review. Respect explicit user requests for effort.
- Follow the spawn tool's context and effort constraints. When an effort override
  requires a fresh context, supply a self-contained assignment with the necessary
  project instructions and evidence.
- Give each assignment its objective, relevant context, file ownership or read-only
  scope, acceptance criteria, and expected evidence. Give inspectors the diff,
  baseline, requirements, and available test results.
- Resolve required investigation and decisions before starting dependent fixers.
  Parallelize independent work with distinct file ownership to avoid edit conflicts.
- Integrate changes before reviewing the combined result. Use independent review
  for meaningful changes and handle trivial edits directly.
- Resolve missing context and scope dependencies in the primary agent, then resume
  the subagent with the additional context. Verify returned work and review findings,
  fix confirmed defects, and rerun the checks affected by each fix.

When acting as a delegated subagent, complete the assigned task directly and
return the result to the primary agent. Leave further delegation to the primary.
