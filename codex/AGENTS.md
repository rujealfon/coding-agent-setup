## Delegation

Apply this delegation policy in Codex sessions.

When acting as the primary agent, implement cohesive tasks directly. Delegate
substantial independent work when parallel progress or a separate assessment
materially improves speed or quality. Keep scope decisions, integration, and final
verification in the primary agent. Respect explicit requests to work without
subagents.

- Use `runner` for bounded read-only lookups, file discovery, and factual checks.
- Use `tracker` to trace behavior, dependencies, and likely causes across files
  without editing code.
- Use `fixer` to implement a defined change within assigned files and verify it.
- Use `inspector` for independent assessment of a specified diff for correctness,
  regressions, security issues, and missing validation.
- Use `consultant` before dependent implementation when architecture or design
  trade-offs remain unresolved, or when two evidence-based attempts have not fixed
  a difficult bug. Provide relevant context, constraints, options, and previous
  attempts. Use sparingly for decisions requiring deeper reasoning; the primary
  agent resolves the recommendation before assigning dependent work.
- Use `default` for bounded mixed investigation and implementation when no
  specialist fits.
- Use each agent's configured model. Choose supported effort at spawn time:
  runner low; tracker, fixer, inspector, and default medium; consultant low for
  bounded advice. Raise effort for consequential unresolved decisions or complex
  investigation, implementation, or security review. Respect explicit user effort
  requests; route simple lookups to runner rather than default.
- Prefer fresh, bounded context when supported. Include relevant project
  instructions, requirements, and evidence rather than unrelated history. Follow
  the spawn tool's context and effort constraints; supply a self-contained
  assignment when selecting effort requires a fresh context.
- Give each assignment its objective, relevant context, file ownership or read-only
  scope, acceptance criteria, and expected evidence. Give inspectors the diff,
  baseline, requirements, and available test results.
- Resolve required investigation and decisions before starting dependent fixers.
  Parallelize independent work with distinct file ownership to avoid edit conflicts.
- Integrate changes before reviewing the combined result. Use independent review
  for meaningful changes, including authentication, authorization, encryption,
  migrations, and data integrity. Solo implementation can still receive a scoped
  inspector review. Keep reviewers' responsibilities distinct when multiple
  reviews are required by project instructions or skills.
- Assign focused checks to workers and repository-wide verification to the primary
  agent after integration and review fixes. Reuse reported evidence; rerun checks
  when subsequent changes, failures, or unresolved concerns justify it.
- Resolve missing context and scope dependencies in the primary agent, then resume
  the subagent with the additional context. Verify returned work and review findings,
  fix confirmed defects, and rerun the checks affected by each fix.

When acting as a delegated subagent, complete the assigned task directly and
return the result to the primary agent. Leave further delegation to the primary.
