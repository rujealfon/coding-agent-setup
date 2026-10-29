# Context and token use

Keep one cohesive objective per session. At a natural boundary before unrelated
work or a substantial new phase, offer a fresh-session handoff. Finish authorized
work first. The handoff should record objective, repository/branch/commit, decisions,
remaining work, checks and log paths, and authorization limits. Read that handoff
in the new session instead of copying the whole conversation.

Delegate substantial independent work or assessments that improve quality. Use
fresh bounded context when supported, and reuse an agent for related follow-up.
Keep configured models. Start routine work and reviews at medium effort; use low
for runner and bounded consultant tasks. Raise effort for a specific difficult
issue or explicit request, stating the reason in the assignment. Preserve required
independent reviews and project checks.

Read relevant skills once per agent, references only when needed; reread changed
or lost material. Keep searches, diffs, and tool output scoped. Reuse verification
that remains valid after subsequent changes. Return concise evidence and blockers.

## Optional Codex fallback

Custom agent files intentionally omit fixed effort so assignments can select it.
For a medium fallback, merge this setting into ~/.codex/config.toml:

```toml
[agents]
default_subagent_reasoning_effort = "medium"
```

Keep one [agents] table and preserve its other settings. Explicit spawn effort
can override this fallback; a custom agent's fixed effort takes precedence. The
installer leaves personal config.toml unchanged. Start a fresh session to load
updated configuration and instructions.

## Measure comparable tasks

From a detective-crew-agents clone, use the read-only standard-library reporter:

```sh
python3 -B tools/session-usage.py list --cwd /path/to/project
python3 -B tools/session-usage.py turns --session SESSION_ID
python3 -B tools/session-usage.py report --session SESSION_ID --from-turn START_TURN --through-turn END_TURN
python3 -B tools/session-usage.py report --session SESSION_ID --format json
```

Run these commands from the clone, or use its absolute tool path. The reporting
tool is not installed or published with the agent configuration. See the clone's
docs/session-usage.md for accounting limitations and options. It reads local
uncompressed JSONL; missing or compressed logs may leave usage unaccounted.

Save private snapshots under ~/.codex/usage/, labeled with session ID and task.
Compare matched task scope, model, effort, checks, and outcome. Track uncached
input, cached input, output, response count, and main/subagent shares separately.
Reasoning is already included in output. Itemize automatic approval usage and
inspect warnings and unaccounted agents. Local totals are not a bill; differing
tasks cannot establish causal savings. Keep personal session IDs and audit
snapshots outside this distributable configuration.

Official references:
- https://learn.chatgpt.com/docs/agent-configuration/subagents
- https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra
