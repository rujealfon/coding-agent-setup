## Delegation

Apply this delegation policy in Claude Code sessions.

When acting as the primary agent, delegate independent work when it materially
improves speed or quality. Handle small tasks directly and keep orchestration,
scope decisions, integration, and final verification in the primary agent.

- Use `fast` for bounded read-only lookups, file discovery, and factual checks.
- Use the built-in `Explore` agent for tracing behavior across the codebase and
  `Plan` for research during plan mode. Include relevant project constraints in
  their assignments because these built-ins skip CLAUDE.md.
- Use `worker` to implement a defined change within assigned files and verify it.
- Use `reviewer` for independent assessment of a supplied diff for correctness,
  regressions, security issues, and missing validation.
- Use the built-in `general-purpose` agent for mixed investigation and action
  when no specialist fits. It can spawn agents, so tell it in the assignment not
  to delegate further.
- Use each agent's configured model. Choose a supported reasoning effort for its
  task: low for simple lookups, medium for routine implementation, and high for
  complex investigation or review. Respect explicit user requests for effort.
- Pass the chosen effort through the Agent tool's per-invocation effort parameter
  for non-fork subagents. This requires v2.1.292 or later. If unavailable, use the
  session default and report that limitation. Respect the
  `CLAUDE_CODE_EFFORT_LEVEL` environment override when set.
- Give each assignment its objective, relevant context, file ownership or read-only
  scope, acceptance criteria, and expected evidence. Give reviewers the diff,
  baseline, requirements, and available test results; their tools cannot run git
  or tests.
- Resolve required investigation and decisions before starting dependent workers.
  Parallelize independent work with distinct file ownership to avoid edit conflicts:
  list the owned files in each assignment, make sure no two workers share one, and
  run work that must touch the same file sequentially.
- Integrate changes before reviewing the combined result. Use independent review
  for meaningful changes and handle trivial edits directly.
- Resolve missing context and scope dependencies in the primary agent, then resume
  the subagent with the additional context. Verify returned work and review findings,
  fix confirmed defects, and rerun the checks affected by each fix.

When acting as a delegated subagent, complete the assigned task directly and
return the result to the primary agent. Leave further delegation to the primary.
