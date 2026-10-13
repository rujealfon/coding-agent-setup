## Delegation

Apply this delegation policy in OpenCode sessions.

When acting as the primary agent, use subagents when independent work can run
in parallel and delegation would materially improve speed or quality. Handle
small tasks directly.

- Use `runner` for simple lookups, targeted searches, and mechanical checks.
- Use the built-in `explore` agent for investigation across files without code edits.
- Use `fixer` to implement a defined change within assigned files and verify it.
- Use `inspector` for independent assessment of correctness, regressions, security
  issues, and missing validation. Supply its diff, baseline, and test results;
  its inspection permissions exclude shell execution and edits.
- Use the built-in `general` agent for mixed investigation and implementation
  when no specialist fits.
- Use each agent's configured model and effort variant.
- Give each agent a bounded task, relevant context, constraints, acceptance
  criteria, and expected output.
- Run dependent tasks in order and parallelize only independent work. Assign
  file edits to agents with distinct ownership to avoid overlapping changes.
- Verify returned work before incorporating it. Resolve scope dependencies and
  missing context before continuing dependent work.

When acting as a delegated subagent, complete the assigned task directly and
return the result to the primary agent.
