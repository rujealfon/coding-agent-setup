# coding-agent-setup

Personal subagent definitions and delegation rules for Codex, Claude Code,
OpenCode v2, and Grok Build. Codex and OpenCode get six roles, Claude Code
and Grok Build get four.
Each role has a configured model. Claude Code, OpenCode, and Grok Build also set
an effort on each role. Codex omits a fixed effort so the primary agent chooses
one for each task. Claude's primary agent can still pass an effort when spawning.
The delegation rules apply across projects on the machine where you install them.

## Models and roles

Meet the **Detective Crew**: Runner gathers facts, Fixer implements the agreed
solution, Inspector checks the resulting change, Consultant recommends an
approach when the decision is difficult, and Tracker follows leads through
the codebase.
The primary agent coordinates the case, makes decisions, integrates changes, and
verifies the outcome. Each tool gets the crew members listed below.

| Crew member | Question it answers | Expected result |
| --- | --- | --- |
| **Runner** | Where is it, and what are the facts? | A concise answer with file or source references |
| **Fixer** | Can you implement the agreed solution? | Scoped changes, relevant checks, and their outcomes |
| **Inspector** | Does this change work correctly, and what did we miss? | Concrete findings with impact and evidence, or no findings with verification limits |
| **Consultant** | Which approach should we take, and why? | A recommendation, alternatives, trade-offs, risks, and supporting evidence |
| **Tracker** (Codex only) | How does this work, and what caused the problem? | Execution paths, likely causes, evidence, and remaining uncertainty |

| Tool | `runner` | `fixer` | `inspector` | `consultant` | `tracker` | `default` | `explore` | `general` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Codex | `gpt-6-luna` | `gpt-6.1-sol` | `gpt-6.1-sol` | `gpt-6-astra` | `gpt-6-luna` | `gpt-6.1-sol` | N/A | N/A |
| Claude Code | `claude-haiku-5-5`, medium | `claude-sonnet-5-5`, medium | `claude-sonnet-5-5`, high | `claude-opus-5-5`, high | N/A | N/A | N/A | N/A |
| OpenCode | `opencode-go/muse-spark-1.3-contributor`, high | `opencode-go/deepseek-v4.1-flash`, max | `opencode-go/deepseek-v4.1-flash`, max | `opencode-go/glm-5.3-flash`, max | N/A | N/A | `opencode-go/muse-spark-1.3-contributor`, high | `opencode-go/deepseek-v4.1-flash`, max |
| Grok Build | `grok-4.7`, low | `grok-4.7`, medium | `grok-4.7`, high | `grok-4.7`, xhigh | N/A | N/A | N/A | N/A |

- `runner` performs simple lookups, targeted searches, and mechanical checks.
- `fixer` implements defined changes within clear file ownership and verifies the affected behavior.
- `inspector` independently assesses correctness, regressions, security issues, and missing validation with read-only tools.
- `consultant` (all four providers) advises on architecture, design trade-offs, and stubborn bugs with inspection tools. It uses Astra in Codex, Opus at high effort in Claude Code, GLM-5.3-Flash at max in OpenCode, and Grok 4.7 at xhigh in Grok Build; the primary agent stays on your main model. See [consultation and handoffs](#consultation-and-handoffs) for when to call it.
- `tracker` (Codex only) traces behavior, dependencies, and likely causes across files without editing code.
- `default` is Codex's subagent for bounded mixed investigation and implementation when no specialist fits. Prefer Fixer for a defined change and Tracker for tracing.
- `explore` is OpenCode's built-in subagent for tracing behavior, dependencies, and likely causes without code edits. Prefer Runner for bounded factual lookups.
- `general` is OpenCode's built-in subagent for bounded mixed investigation and implementation when no specialist fits. Prefer Fixer for a defined change and Explore for tracing.

N/A means this setup does not provide that role for the tool. The model table
shows configured defaults; Claude Inspector escalates to Opus for the riskiest
change types, as described below.

Each provider has its own delegation policy. Those policies route deeper
investigation to Codex `tracker`, OpenCode
`explore`, or Claude Code's built-in `Explore` when available. Mixed work goes
to Codex `default`, OpenCode `general`, or Claude Code's built-in
`general-purpose` when available. These Claude built-ins keep their own model
settings; this setup configures only Claude's four custom roles.
For tools without a matching specialist, the primary agent handles the work or
splits it into scoped assignments for available agents.

### Consultation and handoffs

Use the stages the case needs: gather evidence → consult when needed → implement
→ inspect. The primary agent handles small tasks directly and selects specialists
when delegation improves speed or quality.

Call Consultant before dependent implementation when an architecture or design
decision remains unresolved. Examples include choosing a module boundary, deciding
where state should live, or comparing migration strategies with different risks.
Architecture consultation can happen immediately; the two-attempt threshold
applies to stubborn bugs. For those bugs, consult after two evidence-based attempts
have failed, supplying each hypothesis, attempted fix, and observed result.

Give Consultant a specific decision or diagnostic question, relevant code and
evidence, constraints, viable options, and previous attempts when applicable. It
returns a recommendation with alternatives, risks, and supporting evidence. For
a bug, it also identifies the likely cause, evidence for and against it, and the
cheapest check that would confirm it. The primary agent resolves open questions
and decides the approach before assigning dependent implementation.

Tracker gathers and traces evidence; Consultant uses that evidence to evaluate
an uncertain approach. Inspector reviews the implemented change against its
requirements. An inspector finding may expose a design question that the primary
agent routes back to Consultant.

Use the corresponding investigation role for each provider: Codex `tracker`,
OpenCode `explore`, or Claude's built-in `Explore`. Grok delegates bounded lookups
to Runner and keeps deeper tracing in the primary agent. Its Consultant advises on
unresolved design choices; the primary agent makes the final decision.

For example, a failing test with a clear cause can go directly to Fixer and then
Inspector. A change with competing designs may need Tracker to map the current
behavior, Consultant to compare options, Fixer to implement the chosen approach,
and Inspector to review the combined diff. Give Fixer file ownership and acceptance
criteria; give Inspector the baseline, diff, requirements, and validation results.

### Claude orchestration

The four custom roles complement Claude's built-in agents. Keep coordination,
scope decisions, integration, and final verification in the primary conversation.

| Agent | Assignment | Configuration |
| --- | --- | --- |
| `runner` | Bounded factual lookup or file discovery with references | Haiku 5.5, medium; max 15 turns, reports from 12 tool calls; Read, Glob, Grep, WebFetch, WebSearch |
| `fixer` | Implement an agreed change within owned files and verify it | Sonnet 5.5, medium; no turn limit; inherited tools, including shell, editing, skills, and MCP; Agent disabled |
| `inspector` | Review a supplied diff for concrete defects and explain their impact | Sonnet 5.5, high; max 60 turns, reports from 50 tool calls; Read, Glob, Grep, WebFetch, WebSearch |
| `consultant` | Advise on architecture, design trade-offs, and stubborn bugs; use sparingly | Opus 5.5, high; max 30 turns, reports from 24 tool calls; Read, Glob, Grep, WebFetch, WebSearch |
| `Explore` built-in | Trace behavior and dependencies across the codebase | Built-in read-only tools |
| `Plan` built-in | Gather research during plan mode | Built-in read-only tools |
| `general-purpose` built-in | Mixed investigation and action without a matching specialist | Built-in available tools |

Use only the stages the task needs. For a change that needs investigation, gather
evidence first, then assign fixers distinct file ownership and acceptance
criteria. Integrate their changes before reviewing the combined diff. Give the
inspector the baseline, diff, requirements, and test output: its inspection-only
tools cannot run git or tests. The primary agent validates findings, coordinates
fixes, and checks the result. Independent lookups or fixers can run in parallel;
work that depends on their output waits for it.

Each read-only agent starts writing its report at a tool-call budget, even if
incomplete, and names what it did not verify; the turn limits in the table are
the hard stop. The policy has the primary agent state a tighter budget for a
narrow review or consultation. When a subagent returns partial, hits its turn
limit, or returns no report, resume it with `SendMessage` and ask it to report
now rather than restarting it. `Explore` and `Plan` cannot be resumed; start a
new one.

Fixers lint only their owned files with the repo's own linter, never run a test
project that shares a database with another running fixer, and leave the full
lint, type-check, and test suites to the primary agent, which runs them once
after integration and never two test runs at once. This overrides a project's
pre-handoff checks. A fixer that writes docs, ADRs, or API descriptions gets the
implementing diff or file paths and checks each claim against that code. The
policy also prefers the configured `inspector` over plugin reviewer agents, and
tells agents to search with Grep and Glob and edit with Edit rather than shell
`grep`/`find`, `sed -i`, or scripted replacement.

Explore and Plan skip CLAUDE.md, so include relevant project constraints in their
assignments. Fixers retain inherited tools for project-specific workflows but
cannot spawn further subagents through Agent. Runner, inspector, and consultant use explicit
inspection tool lists, which also exclude shell, edits, and MCP tools. Send work
requiring those tools to the primary agent or a suitably scoped fixer.
The four custom agents have configured model and effort defaults. High-risk
changes always get a review from the default Inspector. For the riskiest of them,
the Opus types, the primary agent also runs one Opus Inspector review at medium
effort without asking first. [claude/docs/opus-review.md](claude/docs/opus-review.md)
lists the Opus types and the review steps; the delegation rule names the types
and points there, so the steps load only when a diff needs them. Approving a plan
does not replace review. Other custom agents use their configured models.

Claude's policy consults before recommending on architecture or design questions,
including data models, APIs, integrations, and hard-to-reverse choices, except
obvious answers and small lookups. It also consults after two failed bug-fix
attempts. For non-trivial changes, meaning those that span more than one module or
touch routing, guards, schema, or tests, the primary agent plans and delegates
implementation. Include the instruction to leave further delegation to the primary
agent when assigning Claude's built-in `general-purpose` agent.

Add another custom role only for a recurring task with distinct tools or
instructions that these roles and the built-ins do not cover.
[Claude routing and tools](https://code.claude.com/docs/en/sub-agents)

### OpenCode orchestration

The six roles combine four custom agents with the built-in `explore` and `general`
subagents. Keep coordination, decisions, integration, and final verification in
the primary agent.

| Agent | Assignment | Configuration |
| --- | --- | --- |
| `runner` | Bounded factual lookup or file discovery | Muse Spark 1.3 Contributor, high; inherited permissions |
| `fixer` | Implement an agreed change and verify it | DeepSeek V4.1 Flash, max; inherited permissions |
| `inspector` | Review a supplied diff for concrete defects | DeepSeek V4.1 Flash, max; inspection tools |
| `consultant` | Advise on unresolved design choices and stubborn bugs | GLM-5.3-Flash, max; inspection tools |
| `explore` | Trace behavior and dependencies across files | Muse Spark 1.3 Contributor, high; built-in exploration permissions |
| `general` | Mixed investigation and implementation | DeepSeek V4.1 Flash, max; built-in general permissions |

Follow the [consultation and handoff guidance](#consultation-and-handoffs), using
`explore` for codebase tracing. Inspector and Consultant use different models to
provide different perspectives; this setup does not assume a universal capability
ranking between them. Revisit the split based on the quality of their findings and
recommendations on your projects.

Inspector and Consultant deny all permissions, then allow only `read`,
`glob`, `grep`, `webfetch`, and `websearch`. Shell execution, edits, and further
subagents stay denied. Supply relevant command output with their assignments and
run validation through the primary agent or Fixer. All roles keep their configured
model variants. Runner uses inspection operations by instruction but inherits
permissions; its prompt is not a permission boundary.

The `explore` and `general` overrides set only model and description, retaining
their built-in system prompts and permissions. Their assignments carry evidence,
ownership, validation, and handoff requirements from the delegation policy.
Further delegation stays with the primary agent; OpenCode's built-in `general`
also blocks child delegation. Start a fresh OpenCode session after installing.
[OpenCode V2 agents and permissions](https://opencode.ai/v2/docs/agents)

### Grok orchestration

The four custom agents use the same model with different reasoning efforts.
Consultant reserves xhigh reasoning for unresolved architecture or design decisions
and bugs that survive two evidence-based attempts; Inspector keeps high effort
for independent review. The primary agent gathers any deeper tracing evidence,
resolves recommendations, assigns implementation, and verifies the combined result.

| Agent | Assignment | Configuration |
| --- | --- | --- |
| `runner` | Bounded factual lookup or file discovery | Grok 4.7, low; inherited capabilities |
| `fixer` | Implement an agreed change and verify it | Grok 4.7, medium; inherited capabilities |
| `inspector` | Review a supplied diff for concrete defects | Grok 4.7, high; read-only capability mode |
| `consultant` | Advise on unresolved design choices and stubborn bugs | Grok 4.7, xhigh; read-only capability mode |

Follow the [consultation and handoff guidance](#consultation-and-handoffs). Supply
Inspector and Consultant with relevant command output, since their capability mode
excludes shell execution and edits. Runner uses inspection operations by instruction
but inherits capabilities. All roles leave integration and further delegation to
the primary agent. The installer preserves your main model and Grok settings.
Start a fresh Grok session after installing.
[Grok subagent configuration](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/16-subagents.md)
[Grok 4.7 reasoning efforts](https://docs.x.ai/developers/grok-4-7)

### Codex orchestration

The six roles cover narrow lookup, codebase investigation, implementation,
independent review, consultation, and mixed work. Keep coordination and final
verification in the primary agent; these custom agents return their assigned work
directly.

| Agent | Assignment | Configuration |
| --- | --- | --- |
| `runner` | Bounded factual lookup or file discovery with references | Luna; read-only sandbox |
| `fixer` | Implement an agreed change within owned files and verify it | Sol; inherited permissions |
| `inspector` | Review a specified diff for concrete defects and explain their impact | Sol; read-only sandbox |
| `consultant` | Advise on architecture, difficult trade-offs, and stubborn bugs | Astra; read-only sandbox |
| `tracker` | Trace behavior, dependencies, and likely causes across files | Luna; read-only sandbox |
| `default` | Bounded mixed investigation and implementation without a matching specialist | Sol; inherited permissions |

Implement cohesive tasks in the primary agent. Delegate substantial independent
workstreams when parallel progress or separate assessment earns the overhead.
Use independent review for meaningful changes, including authentication,
authorization, encryption, migrations, and data integrity; solo implementation
can still receive a scoped Inspector review.

Prefer fresh, bounded assignments containing the relevant project instructions,
requirements, and evidence. Keep responsibilities distinct when project rules
require multiple reviews. Workers run focused checks; the primary agent owns
repository-wide verification after integration and review fixes, repeating checks
when later changes or unresolved concerns justify it.

Give each assignment its objective, relevant context, file ownership or read-only
scope, acceptance criteria, and expected evidence. Gather any required investigation
before starting fixers. Parallelize independent work with distinct file ownership,
then integrate before reviewing the combined change. Supply inspectors with the
baseline, requirements, and validation results. The primary agent verifies findings,
coordinates fixes, and reruns affected checks. Use only the stages a task needs.

Follow the [consultation and handoff guidance](#consultation-and-handoffs) when
choosing between Fixer, Inspector, Consultant, and Tracker.

Runner, tracker, inspector, and consultant are configured with `sandbox_mode = "read-only"`.
Codex can reapply parent runtime permission overrides when spawning, so these are
sandbox defaults rather than an unconditional guarantee. A filesystem sandbox also
does not make external connector tools read-only. Their prompts require inspection
operations across tools. An inspector can inspect git history or diffs through available
read-only commands; send checks that need writes to the primary agent or a fixer.

Fixers and default agents retain inherited project tools. Further delegation is
left to the primary agent by instruction, rather than a Claude-style Agent tool
restriction. All six roles retain their configured models and omit fixed effort.
An ambiguous task or weak result should return to the primary agent for a clearer
assignment or different specialist, rather than spawning an additional hierarchy.
[Codex agent configuration and permissions](https://learn.chatgpt.com/docs/agent-configuration/subagents)

Edit the provider-specific policies listed below to change how each tool delegates
work; the Codex policy defaults to solo implementation for cohesive tasks.

These definitions configure subagents. Select your daily main model separately
in the tool's model selector or settings. The installer does not set the main
model, main effort, or default primary agent. The Codex `default` definition is
a subagent role.

Codex agent files omit `model_reasoning_effort` so the primary agent can select
an effort when spawning each subagent. The Codex policy uses these task-selection
targets, with escalation for more demanding work:

| Role | Usual effort | Escalation |
| --- | --- | --- |
| `runner` | Low | Medium for ambiguous lookups |
| `tracker` | Medium | High for complex investigation |
| `fixer`, `default` | Medium | High for difficult implementation or persistent failures |
| `inspector` | Medium | High for complex or security-sensitive review |
| `consultant` | Low for bounded advice | Medium or high for consequential unresolved decisions |

Keep the configured model roster. A role consumes tokens when invoked; assigning
Sol to multiple roles does not itself incur usage. Trial cheaper implementation
models on bounded mechanical tasks before changing general implementation or
review roles. Compare uncached input, cached input, output, elapsed time, findings,
and corrective work on matched tasks. Different-task token totals do not establish
causal savings, and usage records are not a final bill.

Use effort levels supported by the selected model.
This is a choice made at spawn time. Omitting the field alone uses Codex's
resolved default or inherited effort; it does not enable automatic task-based
selection. Custom agent files that explicitly set effort override spawn settings.
[Codex subagent settings](https://learn.chatgpt.com/docs/agent-configuration/subagents)

For existing installations, run `npx @rujealfon/coding-agent-setup --update` to replace
the earlier definitions and delegation policy with backups. The installer leaves
`~/.codex/config.toml` unchanged. If you want the model default as the fallback
when no effort is selected at spawn time, remove
`default_subagent_reasoning_effort` from its `[agents]` table. Explicit spawn
effort takes precedence over that global default either way.

Claude agent files set a default `effort` in their frontmatter: medium for `runner`
and `fixer`, and high for `inspector` and `consultant`. The delegation
policy also asks the primary agent to pass a supported effort level through the
Agent tool for each non-fork subagent invocation: low for simple lookups, medium
for routine implementation, and high for complex investigation or review.
`CLAUDE_CODE_EFFORT_LEVEL`, if set, overrides per-invocation choices.
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

Grok Build uses `grok-4.7` for all four native agents, with low effort for
`runner`, medium for `fixer`, high for `inspector`, and xhigh for `consultant`.
Inspector and Consultant set `capabilityMode: read-only`, which excludes file
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
Installed paths are unchanged. Run `npx @rujealfon/coding-agent-setup --update` to replace
recognized shared policies with the provider-specific versions and retain backups.
Customized instructions still stop the update before any files are changed.

Claude's Opus review steps install into `~/.claude/docs/opus-review.md`, outside
`~/.claude/rules/`, so they load only when the delegation rule points to them.

Agent definitions install into `~/.codex/agents/`, `~/.claude/agents/`,
`~/.config/opencode/agents/`, and `~/.grok/agents/`, respectively. OpenCode's
built-in role overrides also install into `~/.config/opencode/opencode.jsonc`.

Claude Code supports `~/.claude/CLAUDE.md` as global personal instructions.
It also loads global rules from `~/.claude/rules/`. This setup uses the separate
`delegation.md` rule so you can keep other personal instructions in `CLAUDE.md`.
An empty global `CLAUDE.md` is fine: the delegation rule still loads. There is no
need to duplicate the policy in both files. [Claude global instructions](https://code.claude.com/docs/en/memory#choose-where-to-put-claudemd-files)
and [global rules](https://code.claude.com/docs/en/memory#user-level-rules).

OpenCode's `runner`, `fixer`, `inspector`, and `consultant` definitions live in
`~/.config/opencode/agents/*.md`. Its `explore` and `general` model and description overrides
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

Install the tools you intend to use. You also need Node.js 18 or newer, for
`npx`, and Python 3. The installer uses only Python's standard library. It
installs configuration and does not install the tools or configure credentials.

Run this from any directory:

```sh
npx @rujealfon/coding-agent-setup
```

On a terminal, that opens a checkbox menu titled `Install scope`. Every tool
starts checked, so `All` and each tool are highlighted. The arrow keys move,
Space toggles the current row, and Enter confirms every checked tool. Choosing
`All` checks or clears Codex, Claude, OpenCode, and Grok together. Any
combination can stay checked. A piped or other non-interactive run installs all
four tools.

At least one tool must stay checked, and Ctrl-C cancels with exit status 130.
Pass `--tool` once per tool to choose without the menu, or `--tool all` for every
tool (it cannot be combined with a specific tool). Preview first with `--dry-run`:

```sh
npx @rujealfon/coding-agent-setup --dry-run
npx @rujealfon/coding-agent-setup --tool grok
npx @rujealfon/coding-agent-setup --tool codex --tool grok
```

The custom roles are now named `runner` (formerly `fast`), `fixer` (`worker`),
`inspector` (`reviewer`), and Codex `tracker` (`explorer`). `consultant` replaces
Claude's former `oracle` and is new in the other tools.
Codex `default` and OpenCode’s built-in `explore` and `general` keep their names.
An update backs up and removes recognized old agent files as it installs the new
names. Customized old agents stop the update for manual review.

To upgrade an earlier version of this setup, preview and then apply the update.
`--update` opens an `Update scope` menu on a terminal when you omit `--tool`:

```sh
npx @rujealfon/coding-agent-setup --update --dry-run
npx @rujealfon/coding-agent-setup --update
npx @rujealfon/coding-agent-setup --tool codex --update
```

The installer checks the selected destinations before writing. Identical files stay as
they are. Without `--update`, a recognized earlier version stops the install with
exit status `1` and asks you to rerun with `--update`. With `--update`, it
replaces only files that match recorded earlier versions in [previous-install-hashes.json](previous-install-hashes.json) and saves
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
Otherwise, unless it matches a recorded earlier version that `--update` replaces
with a backup, it reports a conflict before changing any files. Merge the entries
under `agents` from [opencode/opencode.jsonc](opencode/opencode.jsonc) manually.
Configs with JSONC comments or trailing commas still require manual review.

Start fresh tool sessions after installing. To preview installation under another
home directory, add `--target-home /path/to/home --dry-run`. This option is also
useful for testing the installer without changing your personal configuration.

Inside a clone of this repository, `npx` finds this package locally and
runs the `coding-agent-setup` command from `node_modules/.bin`. That link
is included in the clone. The same flags also work through
`python3 install-agents.py`.

## Uninstall

`--uninstall` opens an `Uninstall scope` menu on a terminal when you omit
`--tool`. Preview which installed files would be removed, then remove the
recognized agent definitions and delegation rules:

```sh
npx @rujealfon/coding-agent-setup --uninstall --dry-run
npx @rujealfon/coding-agent-setup --uninstall
npx @rujealfon/coding-agent-setup --tool claude --uninstall
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
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── publish.yml
├── bin/
│   └── coding-agent-setup
├── node_modules/
│   └── .bin/
│       └── coding-agent-setup
├── codex/
│   ├── AGENTS.md
│   ├── consultant.toml
│   ├── default.toml
│   ├── fixer.toml
│   ├── inspector.toml
│   ├── runner.toml
│   └── tracker.toml
├── claude/
│   ├── consultant.md
│   ├── docs/
│   │   └── opus-review.md
│   ├── fixer.md
│   ├── inspector.md
│   ├── runner.md
│   └── rules/
│       └── delegation.md
├── opencode/
│   ├── AGENTS.md
│   ├── consultant.md
│   ├── fixer.md
│   ├── inspector.md
│   ├── opencode.jsonc
│   └── runner.md
├── grok/
│   ├── consultant.md
│   ├── fixer.md
│   ├── inspector.md
│   ├── runner.md
│   └── rules/
│       └── delegation.md
├── tests/
│   ├── fixtures/
│   │   ├── pre-consultant-codex.json
│   │   ├── pre-consultant-grok.json
│   │   ├── pre-consultant-opencode.json
│   │   ├── pre-detective-install.json
│   │   ├── pre-revert-chief-inspector.json
│   │   └── shared-delegation.md
│   ├── test_session_usage.py
│   └── test_uninstall.py
├── tools/
│   └── session-usage.py
├── install-agents.py
├── install-claude-opencode.py
├── package.json
├── previous-install-hashes.json
├── README.md
└── LICENSE
```

| Path | Purpose |
| --- | --- |
| `codex/*.toml` | Codex agent definitions |
| `claude/*.md` | Claude Code agent definitions |
| `opencode/{runner,fixer,inspector,consultant}.md` | OpenCode v2 agent definitions |
| `opencode/opencode.jsonc` | OpenCode v2 built-in `explore` and `general` model and description overrides |
| `grok/*.md` | Grok Build agent definitions |
| `codex/AGENTS.md`, `opencode/AGENTS.md` | Provider-specific global delegation instructions |
| `claude/rules/delegation.md`, `grok/rules/delegation.md` | Provider-specific global delegation rules |
| `claude/docs/opus-review.md` | Claude's Opus review types and steps, reached from its delegation rule |
| `package.json` | npm package `@rujealfon/coding-agent-setup` |
| `bin/coding-agent-setup` | `npx` entry point that runs `install-agents.py` |
| `install-agents.py` | Combined installer and uninstaller for all four tools, or a selected combination |
| `install-claude-opencode.py` | Compatibility entry point that calls the combined installer |
| `previous-install-hashes.json` | Fingerprints of recognized earlier configurations for safe upgrades |
| `.github/workflows/ci.yml` | Installer tests on Ubuntu for pushes, pull requests, and manual runs |
| `.github/workflows/publish.yml` | Runs those tests on `main`, then publishes when the version is not already on npm |
| `tools/session-usage.py` | Read-only local Codex session usage report; not installed or published |
| `tests/test_uninstall.py` | Tests installation, upgrades, removal, and preservation in temporary home directories |
| `tests/test_session_usage.py` | Synthetic tests for the local Codex usage report |
| `tests/fixtures/shared-delegation.md` | Frozen shared policy for upgrade regression tests |
| `tests/fixtures/pre-*.json` | Recorded earlier installs for upgrade regression tests |

The installer resolves source files relative to its own location, so the clone
can live anywhere. Repository files are the editable source; installed copies
are the configuration each tool reads.

Configuration syntax and installer behavior have been checked locally. Live
delegation and access to every configured model have not been verified.
Grok Build 1.0.46 discovers the native agents and delegation rule in a temporary
home directory with `grok inspect --json`.

[CI](.github/workflows/ci.yml) runs the installer tests on Ubuntu with Python 3.13
for pushes, pull requests, and manual runs. The suite uses only the standard
library and installs into temporary home directories.
[Publish](.github/workflows/publish.yml) runs the same tests after a push to
`main`, then publishes the package when its version is not already on npm.

Run the tests with Python's standard library:

```sh
python3 -B -m unittest discover -s tests -v
```

Agent format references: [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Claude subagents](https://code.claude.com/docs/en/sub-agents), and
[OpenCode v2 agents](https://opencode.ai/v2/docs/agents). Grok Build references:
[subagents](https://docs.x.ai/build/features/subagents) and
[agent definitions](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-agent/README.md).

## Local Codex usage reports

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

## License

[MIT](LICENSE), copyright 2026 Ruje Alfon.
