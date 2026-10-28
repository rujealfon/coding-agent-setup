# Local Codex usage reports

From a clone, run the read-only reporting tool with Python 3.9 or newer. It uses
only the standard library; it is not installed into your personal agent config
or included in the npm package. By default it reads `~/.codex/sessions`.

```sh
python3 -B tools/session-usage.py list --cwd /path/to/project
python3 -B tools/session-usage.py turns --session SESSION_ID
python3 -B tools/session-usage.py report --session SESSION_ID \
  --from-turn START_TURN --through-turn END_TURN
python3 -B tools/session-usage.py report --session SESSION_ID \
  --from-turn START_TURN --through-turn END_TURN --format json > /tmp/usage.json
```

Use the full IDs from `list` and `turns`. Turn listings contain timestamps and
resolved model/effort, not message text. Omit the turn bounds to report the whole
recorded session. Both bounds are inclusive. To inspect a smaller log directory,
put `--sessions-dir /path/to/sessions` before the subcommand.

Reports group usage by agent, model, and resolved effort, and include input,
cached and uncached input, output, and reasoning as a subset of output, with cache
writes in the totals when recorded. They sum per-response
`token_usage_record.usage`, deduplicate response IDs, and never add cumulative counters. Conflicting duplicates use the
latest timestamp and produce a warning. Older logs containing only cumulative
counters are reported as unknown, not converted into zero usage. Missing or
invalid records produce warnings; totals represent the known attributable usage.
Selected turns or known active agents without response records appear under
`unaccounted` with unknown usage. Even a valid report cannot prove that no log
files are missing. The local log format is not a stable public API, so unsupported formats need
inspection before their numbers can be trusted.

Root usage is selected by turn ID. Subagents, including agents spawned earlier
and reused during the task, are selected by response timestamp inside the root
turn range. Calls crossing a boundary and concurrent unrelated agent work can
therefore affect attribution. Use repeatable `--exclude-agent /root/agent_name`
(or a thread ID) to exclude consultations or unrelated work explicitly. Automatic
approval agents are excluded by default and itemized separately; use
`--include-automatic` to include their recorded usage. These totals are not a bill
and do not establish causal savings between different tasks.

Elapsed time spans the first selected turn start through the last selected turn
end. For a known interruption, use repeatable ISO UTC-offset ranges:

```sh
python3 -B tools/session-usage.py report --session SESSION_ID \
  --pause 2026-10-20T08:24:00Z/2026-10-20T12:44:00Z
```

Overlapping pauses are merged for duration and clipped to the selected range.
Pauses adjust elapsed time only; usage during them stays counted. An incomplete
last turn ends at its latest recorded root usage and carries a warning. No dollar
estimate is calculated. Reports export only accounting and identifying metadata,
not prompts, tool output, credentials, or source contents. They still contain
local directory paths and session/agent identifiers; review them before sharing.
Malformed-record warnings identify the file and line without echoing its contents.
JSON and Markdown reports go to stdout; command errors go to stderr with exit 2.
A report with incomplete accounting can still exit 0: inspect its warnings and
accounting fields. Listing warnings go to stderr in Markdown mode.

The existing CI unittest command also runs synthetic reporting tests. Live log
checks are read-only and require no model calls. The `compare` subcommand and
monetary estimates are deferred until the accounting has been exercised further.
