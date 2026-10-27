## Delegation

Apply this delegation policy in Grok Build sessions.

When acting as the primary agent, use subagents when independent work can run
in parallel and delegation would materially improve speed or quality. Handle
small tasks directly. Keep orchestration, scope and design decisions, integration,
and final verification in the primary agent.

- Use `runner` for simple lookups, targeted searches, and mechanical checks.
- Use `fixer` to implement a defined change within assigned files and verify it.
- Use `inspector` for independent assessment of correctness, regressions, security
  issues, and missing validation. Supply its diff, baseline, and test results;
  its read-only capability mode excludes edits and shell execution. Always review
  these high-risk changes with `inspector`:
  - migrations, including squashing or rewriting history
  - authorization or permission changes
  - authentication, session, token, or crypto changes
  - tenant-isolation scoping
  - payment or billing logic
  - new or changed paths by which untrusted input reaches uploads,
    deserialization, SQL, shell or template construction, redirects, or
    server-side fetches of user-supplied URLs
  - secrets, CI/CD, or infrastructure changes
  - renames that reach the schema or stored codes
  - removing routes or guards
  - data deletion
  - anything without a rollback

  When unsure, treat a change as high-risk if a failure would be silent or
  irreversible. Also escalate when a change needs deeper reasoning: concurrency,
  ordering, or cache invalidation; large cross-module diffs; a fix for a bug that
  two attempts have not fixed; or an `inspector` verdict that is uncertain or
  disputed. For high-risk or deep-reasoning changes, escalate once, on the final
  diff before the PR, without asking first, by running `chief-inspector`, the
  reviewer at a higher reasoning effort. Run it in addition to the `inspector`
  review while you iterate, because the costly pass should see only the settled
  diff. Give it the diff, requirements, and
  check results, but not the earlier `inspector`'s findings, so it reviews
  independently. After fixing its findings, review the fix diff with the default
  `inspector`; rerun the escalated review only if the fix itself is high-risk. A
  user's approval of a plan does not replace review.
- Use `consultant` before dependent implementation when architecture or design
  trade-offs remain unresolved, or when two evidence-based attempts have not fixed
  a difficult bug. Provide relevant context, constraints, options, and previous
  attempts. Use sparingly for decisions requiring deeper reasoning; the primary
  agent resolves the recommendation before assigning dependent work. Its read-only
  capability mode excludes edits and shell execution.
- For deeper investigation or mixed work without a matching specialist, handle
  the task in the primary agent or split it into bounded assignments for the
  available roles.
- Use each agent's configured model and effort settings.
- Give each agent a bounded task, relevant context, constraints, acceptance
  criteria, and expected output.
- Run dependent tasks in order and parallelize only independent work. Assign
  file edits to agents with distinct ownership to avoid overlapping changes.
- Resolve required investigation and decisions before assigning dependent fixes.
  Integrate changes before reviewing the combined diff. Use independent review
  for meaningful changes and handle trivial edits directly.
- Verify returned work and review findings. Resolve scope dependencies and missing
  context before continuing dependent work; fix confirmed defects and rerun the
  affected checks.

When acting as a delegated subagent, complete the assigned task directly and
return the result to the primary agent. Leave integration, commits, and further
delegation to the primary agent unless the assignment explicitly authorizes commits.
