# Context and token use

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
