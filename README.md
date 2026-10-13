# coding-agent-setup

Personal subagent definitions and delegation rules for Codex, Claude Code,
OpenCode v2, and Grok Build. Codex and OpenCode get five roles; Claude Code
gets four and Grok Build gets three.
Each role has a configured model. Codex and Claude Code reasoning effort is chosen
by the primary agent for each task; other tools keep configured effort levels.
The delegation rules apply across projects on the machine where you install them.

## Models and roles

Meet the **Detective Crew**: Runner gathers facts, Tracker follows leads through
the codebase, Fixer implements solutions, Inspector checks the work, and Consultant
advises on the toughest cases. Each tool gets the crew members listed below.

| Tool | `runner` | `fixer` | `inspector` | `consultant` | `tracker` | `default` | `explore` | `general` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Codex | `gpt-6-luna` | `gpt-6.1-sol` | `gpt-6-astra` | N/A | `gpt-6-luna` | `gpt-6.1-sol` | N/A | N/A |
| Claude Code | Haiku 5.5 | Sonnet 5.5 | Sonnet 5.5 | Opus 5.5 | N/A | N/A | N/A | N/A |
| OpenCode | `opencode-go/muse-spark-1.3-contributor`, high | `opencode-go/deepseek-v4.1-flash`, max | `opencode-go/glm-5.3-flash`, max | N/A | N/A | N/A | `opencode-go/muse-spark-1.3-contributor`, medium | `opencode-go/deepseek-v4.1-flash`, max |
| Grok Build | Grok 4.7, low | Grok 4.7, medium | Grok 4.7, high | N/A | N/A | N/A | N/A | N/A |

- `runner` performs simple lookups, targeted searches, and mechanical checks.
- `tracker` (Codex only) traces behavior, dependencies, and likely causes across files without editing code.
- `fixer` implements defined changes within clear file ownership and verifies the affected behavior.
- `inspector` independently assesses correctness, regressions, security issues, and missing validation with read-only tools.
- `consultant` (Claude Code only) advises on architecture, design trade-offs, and stubborn bugs with read-only tools. It uses Opus at high effort and is meant to be called sparingly; the primary agent stays on your main model.
- `explore` is OpenCode's built-in exploration subagent.
- `general` is OpenCode's built-in general-purpose subagent.

N/A means this setup does not provide that role for the tool.

Each provider has its own delegation policy. Those policies route deeper
investigation to Codex `tracker`, OpenCode
`explore`, or Claude Code's built-in `Explore` when available. Mixed work goes
to Codex `default`, OpenCode `general`, or Claude Code's built-in
`general-purpose` when available. These Claude built-ins keep their own model
settings; this setup configures only Claude's four custom roles.
For tools without a matching specialist, the primary agent handles the work or
splits it into scoped assignments for available agents.

### Claude orchestration

The four custom roles complement Claude's built-in agents. Keep coordination,
scope decisions, integration, and final verification in the primary conversation.

| Agent | Assignment | Tool access |
| --- | --- | --- |
| `runner` | Bounded factual lookup or file discovery with references | Read, Glob, Grep, WebFetch, WebSearch |
| `Explore` built-in | Trace behavior and dependencies across the codebase | Built-in read-only tools |
| `Plan` built-in | Gather research during plan mode | Built-in read-only tools |
| `fixer` | Implement an agreed change within owned files and verify it | Inherited tools, including shell, editing, skills, and MCP; Agent disabled |
| `inspector` | Review a supplied diff for concrete defects and explain their impact | Read, Glob, Grep, WebFetch, WebSearch |
| `consultant` | Advise on architecture, design trade-offs, and stubborn bugs; use sparingly | Read, Glob, Grep, WebFetch, WebSearch |
| `general-purpose` built-in | Mixed investigation and action without a matching specialist | Built-in available tools |

Use only the stages the task needs. For a change that needs investigation, gather
evidence first, then assign fixers distinct file ownership and acceptance
criteria. Integrate their changes before reviewing the combined diff. Give the
inspector the baseline, diff, requirements, and test output: its inspection-only
tools cannot run git or tests. The primary agent validates findings, coordinates
fixes, and checks the result. Independent lookups or fixers can run in parallel;
work that depends on their output waits for it.

Explore and Plan skip CLAUDE.md, so include relevant project constraints in their
assignments. Fixers retain inherited tools for project-specific workflows but
cannot spawn further subagents through Agent. Runner, inspector, and consultant use explicit
inspection tool lists, which also exclude shell, edits, and MCP tools. Send work
requiring those tools to the primary agent or a suitably scoped fixer.
This setup keeps all four custom models fixed and sets a default effort for each. Add another custom role only for a recurring task with distinct tools or
instructions that these roles and the built-ins do not cover.
[Claude routing and tools](https://code.claude.com/docs/en/sub-agents)

### Codex orchestration

The five roles cover narrow lookup, codebase investigation, implementation,
independent review, and mixed work. Keep coordination and final verification in
the primary agent; these custom agents return their assigned work directly.

| Agent | Assignment | Configuration |
| --- | --- | --- |
| `runner` | Bounded factual lookup or file discovery with references | Luna; read-only sandbox |
| `tracker` | Trace behavior, dependencies, and likely causes across files | Luna; read-only sandbox |
| `fixer` | Implement an agreed change within owned files and verify it | Sol; inherited permissions |
| `inspector` | Review a specified diff for concrete defects and explain their impact | Astra; read-only sandbox |
| `default` | Bounded mixed investigation and implementation without a matching specialist | Sol; inherited permissions |

Give each assignment its objective, relevant context, file ownership or read-only
scope, acceptance criteria, and expected evidence. Gather any required investigation
before starting fixers. Parallelize independent work with distinct file ownership,
then integrate before reviewing the combined change. Supply inspectors with the
baseline, requirements, and validation results. The primary agent verifies findings,
coordinates fixes, and reruns affected checks. Use only the stages a task needs.

Runner, tracker, and inspector are configured with `sandbox_mode = "read-only"`.
Codex can reapply parent runtime permission overrides when spawning, so these are
sandbox defaults rather than an unconditional guarantee. A filesystem sandbox also
does not make external connector tools read-only. Their prompts require inspection
operations across tools. An inspector can inspect git history or diffs through available
read-only commands; send checks that need writes to the primary agent or a fixer.

Fixers and default agents retain inherited project tools. Further delegation is
left to the primary agent by instruction, rather than a Claude-style Agent tool
restriction. All five roles retain their configured models and omit fixed effort.
An ambiguous task or weak result should return to the primary agent for a clearer
assignment or different specialist, rather than spawning an additional hierarchy.
[Codex agent configuration and permissions](https://learn.chatgpt.com/docs/agent-configuration/subagents)

The primary agent delegates when independent work can run in parallel and doing
so would improve speed or quality. It handles small tasks directly. Edit the
provider-specific policies listed below to change how each tool delegates work.

These definitions configure subagents. Select your daily main model separately
in the tool's model selector or settings. The installer does not set the main
model, main effort, or default primary agent. The Codex `default` definition is
a subagent role.

Codex agent files omit `model_reasoning_effort` so the primary agent can select
an effort when spawning each subagent. The delegation policy asks it to choose
low for simple lookups, medium for routine implementation, and high for complex
investigation or review, using a level supported by the selected model.
This is a choice made at spawn time. Omitting the field alone uses Codex's
resolved default or inherited effort; it does not enable automatic task-based
selection. Custom agent files that explicitly set effort override spawn settings.
[Codex subagent settings](https://learn.chatgpt.com/docs/agent-configuration/subagents)

For existing installations, run `python3 install-agents.py --update` to replace
the earlier definitions and delegation policy with backups. The installer leaves
`~/.codex/config.toml` unchanged. If you want the model default as the fallback
when no effort is selected at spawn time, remove
`default_subagent_reasoning_effort` from its `[agents]` table. Explicit spawn
effort takes precedence over that global default either way.

Claude agent files set a default `effort` in their frontmatter: low for `runner`,
medium for `fixer`, and high for `inspector` and `consultant`. On Claude Code v2.1.292
or later, the delegation policy also asks the primary agent to pass a supported
effort level through the Agent tool for each non-fork subagent invocation, using
the same task guidance as Codex. On older versions, the primary agent reports the
limitation. `CLAUDE_CODE_EFFORT_LEVEL`, if set, overrides per-invocation choices.
Unset that environment variable to let the primary agent choose effort.
The installer leaves Claude settings and shell environment variables unchanged.
Restart Claude Code after updating to load the new agent definitions.
[Claude subagent effort](https://code.claude.com/docs/en/sub-agents#choose-an-effort-level)

Claude uses explicit `claude-haiku-5-5`, `claude-sonnet-5-5`, and
`claude-opus-5-5` model IDs. OpenCode uses the `opencode-go` provider and encodes
effort as a model variant, such as `#medium`, `#high`, or `#max`. Access to these
models and variants depends on your account and provider. Check that they are available
before using the agents. [Claude models](https://platform.claude.com/docs/en/models/overview),
[OpenAI models](https://developers.openai.com/api/docs/models), and
[OpenCode model variants](https://opencode.ai/v2/docs/models#variants).

Grok Build uses `grok-4.7` for all three native agents, with low effort for
`runner`, medium for `fixer`, and high for `inspector`. The inspector sets `capabilityMode: read-only`, which excludes file
edits and shell execution. These fields follow the
[Grok agent schema](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-agent/src/config.rs).

## Global instructions and installation paths

`~` means your home directory. These paths are personal configuration and apply
across projects; they are separate from instruction files inside a repository.

| Tool | Policy source in this repo | Installed policy |
| --- | --- | --- |
| Codex | [codex/AGENTS.md](codex/AGENTS.md) | `~/.codex/AGENTS.md` |
| Claude Code | [claude/rules/delegation.md](claude/rules/delegation.md) | `~/.claude/rules/delegation.md` |
| OpenCode v2 | [opencode/AGENTS.md](opencode/AGENTS.md) | `~/.config/opencode/AGENTS.md` |
| Grok Build | [grok/rules/delegation.md](grok/rules/delegation.md) | `~/.grok/rules/delegation.md` |

Each policy contains only its provider's roles, effort controls, and delegation
instructions. These destinations match the tools' global instruction discovery:
[Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[Claude user-level rules](https://code.claude.com/docs/en/memory#user-level-rules),
[OpenCode instructions](https://opencode.ai/v2/docs/instructions), and
[Grok rules directories](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/12-project-rules.md#rules-directories).

The former root `delegation.md` has been replaced by these four source files.
Installed paths are unchanged. Run `python3 install-agents.py --update` to replace
recognized shared policies with the provider-specific versions and retain backups.
Customized instructions still stop the update before any files are changed.

Agent definitions install into `~/.codex/agents/`, `~/.claude/agents/`,
`~/.config/opencode/agents/`, and `~/.grok/agents/`, respectively. OpenCode's
built-in role overrides also install into `~/.config/opencode/opencode.jsonc`.

Claude Code supports `~/.claude/CLAUDE.md` as global personal instructions.
It also loads global rules from `~/.claude/rules/`. This setup uses the separate
`delegation.md` rule so you can keep other personal instructions in `CLAUDE.md`.
An empty global `CLAUDE.md` is fine: the delegation rule still loads. There is no
need to duplicate the policy in both files. [Claude global instructions](https://code.claude.com/docs/en/memory#choose-where-to-put-claudemd-files)
and [global rules](https://code.claude.com/docs/en/memory#user-level-rules).

OpenCode's `runner`, `fixer`, and `inspector` definitions live in
`~/.config/opencode/agents/*.md`. Its `explore` and `general` model overrides
live in `~/.config/opencode/opencode.jsonc`.

For project-specific instructions, put `AGENTS.md` or `CLAUDE.md` inside the
repository. Claude Code v2.1.277 and later can load project `AGENTS.md`, with
loading determined by its Project instructions setting and existing project
`CLAUDE.md` files. To share a project `AGENTS.md` through `CLAUDE.md`, add this
line to the project's `CLAUDE.md`:

```markdown
@AGENTS.md
```

That import is a Claude-specific feature. OpenCode v2 reads `AGENTS.md` directly
and does not use `CLAUDE.md` as a fallback. [Claude project instruction loading](https://code.claude.com/docs/en/memory#agentsmd)
and [OpenCode v2 instructions](https://opencode.ai/v2/docs/instructions).

Grok Build loads global rules from `~/.grok/rules/` and project `AGENTS.md`
files. This setup installs native Grok agents and a separate delegation rule;
it does not change `~/.grok/config.toml` or your main model. Project agents under
`.grok/agents/` can override the global agents with the same names. Grok may also
load Claude instruction files and global rules when its compatibility settings
enable them. Each policy states which provider session it applies to. This
installer leaves compatibility settings unchanged.
Use `grok inspect --json` to inspect discovered configuration and `/config-agents`
to check the available agents. See
[Grok instructions](https://docs.x.ai/build/features/project-rules) and
[Grok subagents](https://docs.x.ai/build/features/subagents).

## Install or upgrade

Install the tools you intend to use and have Python 3 available. The installer
uses only Python's standard library. It installs configuration and does not
install the tools or configure credentials.

On a terminal, install, update, and uninstall open a checkbox menu titled
`Install scope`, `Update scope`, or `Uninstall scope`. Every tool starts
checked, so `All` and each tool are highlighted. The arrow keys move, Space
toggles the current row, and Enter confirms every checked tool. Choosing `All`
checks or clears Codex, Claude, OpenCode, and Grok together. Any combination
can stay checked.
A piped or other non-interactive run operates on all four tools. Pass `--tool`
once per tool to make the same choice without a prompt:

```sh
python3 install-agents.py --tool grok
python3 install-agents.py --tool codex --tool grok
python3 install-agents.py --tool codex --update
python3 install-agents.py --tool claude --uninstall
```

From the cloned `coding-agent-setup` directory, preview a fresh installation:

```sh
python3 install-agents.py --dry-run
```

Install the files:

```sh
python3 install-agents.py
```

The custom roles are now named `runner` (formerly `fast`), `fixer` (`worker`),
`inspector` (`reviewer`), `consultant` (`oracle`), and Codex `tracker` (`explorer`).
Codex `default` and OpenCode’s built-in `explore` and `general` keep their names.
An update backs up and removes recognized old agent files as it installs the new
names. Customized old agents stop the update for manual review.

To upgrade an earlier version of this setup, preview and then apply the update:

```sh
python3 install-agents.py --update --dry-run
python3 install-agents.py --update
```

The installer checks the selected destinations before writing. Identical files stay as
they are. With `--update`, it replaces only files that match recorded earlier
versions in [previous-install-hashes.json](previous-install-hashes.json) and saves
a backup beside each changed file as `<filename>.bak-<UTC timestamp>`. Customized
instructions or agents cause it to stop before changing any files. `--update`
does not force replacement of unrecognized files.

If you have existing personal instructions, review the reported conflict and
merge the delegation policy into the appropriate instruction file manually.
Keep your existing instructions. The installer does not perform this merge.

If your customized `~/.config/opencode/opencode.jsonc` uses plain JSON and
already contains all the specified `explore` and `general` agent fields, the
installer preserves the entire file and continues. Extra settings, agents,
and agent fields stay intact. Uninstall still preserves this customized file.
Otherwise, it reports a conflict before changing any files. Merge the entries
under `agents` from [opencode/opencode.jsonc](opencode/opencode.jsonc) manually.
Configs with JSONC comments or trailing commas still require manual review.

Start fresh tool sessions after installing. To preview installation under another
home directory, use `--target-home /path/to/home --dry-run`. This option is also
useful for testing the installer without changing your personal configuration.

## Uninstall

Preview which installed files would be removed:

```sh
python3 install-agents.py --uninstall --dry-run
```

Remove the recognized agent definitions and delegation rules:

```sh
python3 install-agents.py --uninstall
```

Add `--tool opencode` to remove one tool, repeat `--tool` for several, or check
any combination in the menu. Choosing `All` checks every tool.
Uninstall checks the same destinations as installation, limited to the tools you
selected. It removes files that match the current definitions or recorded earlier
versions of this setup.
Customized files, empty personal instruction files, symlinks, and directories
are preserved and reported for manual review. Recognized files are still removed
when other files need manual review; the command exits with status `1` if any
destination was preserved. Missing files are harmless, so you can rerun it.

Customized app settings, credentials, other agents, and upgrade backups stay in place.
The setup-owned OpenCode `opencode.jsonc` is removed when its contents match
the current setup or a recorded earlier version.
Backups are not restored automatically. To recover an earlier instruction file,
review its `.bak-<UTC timestamp>` copy and restore or merge it manually. Start
fresh tool sessions after uninstalling.

Use `--target-home /path/to/home` to uninstall from another home directory.
`--uninstall` and `--update` cannot be combined.

## Repository files

```text
coding-agent-setup/
├── codex/
│   └── AGENTS.md
├── claude/
│   └── rules/delegation.md
├── opencode/
│   └── AGENTS.md
├── grok/
│   └── rules/delegation.md
├── install-agents.py
├── install-claude-opencode.py
├── previous-install-hashes.json
├── tests/
├── README.md
└── LICENSE
```

| Path | Purpose |
| --- | --- |
| `codex/*.toml` | Codex agent definitions |
| `claude/*.md` | Claude Code agent definitions |
| `opencode/{runner,fixer,inspector}.md` | OpenCode v2 agent definitions |
| `opencode/opencode.jsonc` | OpenCode v2 built-in `explore` and `general` model overrides |
| `grok/*.md` | Grok Build agent definitions |
| `codex/AGENTS.md`, `opencode/AGENTS.md` | Provider-specific global delegation instructions |
| `claude/rules/delegation.md`, `grok/rules/delegation.md` | Provider-specific global delegation rules |
| `install-agents.py` | Combined installer and uninstaller for all four tools, or a selected combination |
| `install-claude-opencode.py` | Compatibility entry point that calls the combined installer |
| `previous-install-hashes.json` | Fingerprints of recognized earlier configurations for safe upgrades |
| `tests/test_uninstall.py` | Tests installation, upgrades, removal, and preservation in temporary home directories |
| `tests/fixtures/shared-delegation.md` | Frozen shared policy for upgrade regression tests |

The installer resolves source files relative to its own location, so the clone
can live anywhere. Repository files are the editable source; installed copies
are the configuration each tool reads.

Configuration syntax and installer behavior have been checked locally. Live
delegation and access to every configured model have not been verified.
Grok Build 1.0.46 discovers the native agents and delegation rule in a temporary
home directory with `grok inspect --json`.

Run the tests with Python's standard library:

```sh
python3 -B -m unittest discover -s tests -v
```

Agent format references: [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Claude subagents](https://code.claude.com/docs/en/sub-agents), and
[OpenCode v2 agents](https://opencode.ai/v2/docs/agents). Grok Build references:
[subagents](https://docs.x.ai/build/features/subagents) and
[agent definitions](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-agent/README.md).

## License

[MIT](LICENSE), copyright 2026 Ruje Alfon.
