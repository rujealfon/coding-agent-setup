# Sonnet versus Opus fixer trial — 2026-10-28

Recommendation: keep Sonnet 5.5 as the `fixer` model. On these five seeded
regressions both models passed every case with equivalent patches, and Sonnet was
about 2.2 times faster and about 2.7 times cheaper at list price. This small run
does not show whether Opus does better on harder, unseeded work.

The local Claude Code CLI (2.1.312, Claude login) ran each model once on five
seeded regressions in `tools/session-usage.py`, at medium effort. Each attempt
started in a fresh temporary workspace with the `claude/fixer.md` instructions
(written as `CLAUDE.md`), the mutated source, and the existing 24-test suite. Model
order alternated by case. The CLI ran with project settings only, slash commands
disabled, no session persistence, `acceptEdits` permissions, and tools limited to
Read, Edit, Write, Glob, Grep and `python3` through Bash, with Agent disallowed.
Claude Code has no workspace-write sandbox, so isolation relies on the temporary
directory and that tool list. The host evaluated the resulting source in another
fresh workspace with the original tests. Baseline passed and every seed failed
before model attempts. No retries or human corrective work were supplied.

| Seed | Sonnet seconds | Opus seconds | Trusted tests |
| --- | ---: | ---: | --- |
| Token totals | 8.139 | 20.531 | Both 24/24 |
| Child response time window | 8.139 | 16.208 | Both 24/24 |
| Automatic agent exclusion | 10.332 | 17.744 | Both 24/24 |
| Latest conflicting response | 9.765 | 23.520 | Both 24/24 |
| Overlapping pauses | 9.783 | 23.420 | Both 24/24 |

| Aggregate | Sonnet 5.5 | Opus 5.5 |
| --- | ---: | ---: |
| Attempts passing existing tests | 5/5 | 5/5 |
| Attempts editing files outside the target | 0 | 0 |
| CLI elapsed seconds, total | 46.158 | 101.423 |
| Output tokens | 3,814 | 7,327 |
| Cache read input tokens | 166,723 | 294,052 |
| Cache creation input tokens | 77,050 | 95,096 |
| Uncached input tokens | 30 | 44 |
| List cost, `costUSD` from result events | $0.363 | $0.966 |

Sonnet used 54.5% less total CLI elapsed time and was faster in all five pairs.
Durations include CLI startup and tool use, excluding host scoring. Token counts and
`costUSD` come from the stream-json `result` event; `costUSD` is list-price
accounting, not a bill. Cache state was not controlled, and no subscription credit
or monetary savings are inferred.

Patch review: all ten patches restore the original line exactly, except Sonnet's
latest-response patch, which writes `when < previous["when"]` instead of
`previous["when"] > when`. That is the same comparison. Both models reused the
existing `union_seconds()` helper for pause overlap, so neither changed the
serialized `timing.pauses` records. Benchmark patches were never applied to the
working repository.

Limitations: one attempt per model per seed; one Python module; explicit symptom
hints and visible tests; simple single-line seeded regressions; no hidden tests;
no broad implementation, architecture, or security evaluation. The CLI loaded the
user's Claude login and its list-price accounting, and prompt and runtime overhead
and cache behavior can affect comparisons. Repeat on matched real fixes, including
unseen edge cases and independent review, before treating this as a reliable
general quality or cost comparison.

Reproduce from the repository checkout:

```sh
python3 -B tools/benchmark-fixer.py --provider claude --dry-run
python3 -B tools/benchmark-fixer.py --provider claude --output /tmp/fixer-claude-comparison-new
```

The output directory must be new and outside the checkout. Raw artifacts for this
run (summary JSON and Markdown, per-attempt event logs, final source and patches,
and host evaluator logs) were written to a session scratch directory and may be
cleaned by the operating system. The run completed without infrastructure errors.
