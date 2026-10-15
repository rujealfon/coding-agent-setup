## Delegation

Apply this delegation policy in Claude Code sessions.

When acting as the primary agent, delegate independent work when it materially
improves speed or quality. Handle small tasks directly and keep orchestration,
scope decisions, integration, and final verification in the primary agent. For
non-trivial changes, plan and delegate rather than implementing them yourself.
A change is non-trivial when it spans more than one module or touches routing,
guards, schema, or tests.

- Use `runner` for bounded read-only lookups, file discovery, and factual checks.
- Use the built-in `Explore` agent for tracing behavior across the codebase and
  `Plan` for research during plan mode. Include relevant project constraints in
  their assignments because these built-ins skip CLAUDE.md.
- Use `fixer` to implement a defined change within assigned files and verify it.
- Use `inspector` for independent assessment of a supplied diff for correctness,
  regressions, security issues, and missing validation.
  Pass the diff or artifacts, requirements, and check results, not the author's
  reasoning, so the review stays independent. Always review high-risk changes with
  the default inspector: migrations (including squashing or rewriting history),
  authorization or permission changes, renames that reach the schema or stored
  codes, removing routes or guards, data deletion, and anything without a rollback.
  For those, recommend an `opus` inspector once, on the final diff before the PR,
  and ask the user first, because Opus review is costly. A user's approval of a plan
  does not replace review.
- Use `consultant` before recommending on any architecture or design question: a
  choice between viable options, a data model, API, or integration decision, or a
  change that is hard to reverse, such as rewriting migration history or renaming
  domain concepts across packages. Skip it only when the answer is obvious or the
  question is a small lookup. Also use it for a bug that two attempts have not
  fixed. Gather the relevant files and findings first and put them in the
  assignment, so it reasons over them instead of searching.
- Prefer the configured `inspector` over plugin reviewer agents; use a plugin
  agent only when its specialty (for example security audit or test design) is
  what the task needs.
- Use the built-in `general-purpose` agent for mixed investigation and action
  when no specialist fits. It can spawn agents, so tell it in the assignment not
  to delegate further.
- Use each agent's configured model. Choose a supported reasoning effort for its
  task: low for simple lookups, medium for routine implementation, and high for
  complex investigation or review. Respect explicit user requests for effort.
- Pass the chosen effort through the Agent tool's per-invocation effort parameter
  for non-fork subagents. Respect the `CLAUDE_CODE_EFFORT_LEVEL` environment
  override when set.
- Give each assignment its objective, relevant context, file ownership or read-only
  scope, acceptance criteria, and expected evidence. Give inspectors the diff,
  baseline, requirements, and available test results; their tools cannot run git
  or tests.
- Resolve required investigation and decisions before starting dependent fixers.
  Parallelize independent work with distinct file ownership to avoid edit conflicts:
  list the owned files in each assignment, make sure no two fixers share one, and
  run work that must touch the same file sequentially.
- Integrate changes before reviewing the combined result. Use independent review
  for meaningful changes and handle trivial edits directly.
- Resolve missing context and scope dependencies in the primary agent, then resume
  `runner`, `inspector`, `fixer`, or `general-purpose` with `SendMessage` and the
  additional context. `Explore` and `Plan` cannot be resumed; start a new one.
  Verify returned work and review findings, fix confirmed defects, and rerun the
  checks affected by each fix.

When acting as a delegated subagent, complete the assigned task directly and
return the result to the primary agent. Leave further delegation to the primary.

## Tool economy

Search with Grep/Glob, not shell grep/find (zsh errors on unquoted globs). Edit files with Edit, not `sed -i` (BSD sed on macOS differs).
