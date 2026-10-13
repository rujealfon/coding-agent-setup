## Delegation

Apply this delegation policy in Grok Build sessions.

When acting as the primary agent, use subagents when independent work can run
in parallel and delegation would materially improve speed or quality. Handle
small tasks directly.

- Use `runner` for simple lookups, targeted searches, and mechanical checks.
- Use `fixer` to implement a defined change within assigned files and verify it.
- Use `inspector` for independent assessment of correctness, regressions, security
  issues, and missing validation. Supply its diff, baseline, and test results;
  its read-only capability mode excludes edits and shell execution.
- For deeper investigation or mixed work without a matching specialist, handle
  the task in the primary agent or split it into bounded assignments for the
  available roles.
- Use each agent's configured model and effort settings.
- Give each agent a bounded task, relevant context, constraints, acceptance
  criteria, and expected output.
- Run dependent tasks in order and parallelize only independent work. Assign
  file edits to agents with distinct ownership to avoid overlapping changes.
- Verify returned work before incorporating it. Resolve scope dependencies and
  missing context before continuing dependent work.

When acting as a delegated subagent, complete the assigned task directly and
return the result to the primary agent.
