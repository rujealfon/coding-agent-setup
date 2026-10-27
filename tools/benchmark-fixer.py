#!/usr/bin/env python3
"""Run a local, seeded fixer smoke benchmark; requires Python 3.9+ and the Codex or Claude Code CLI."""
import argparse
import difflib
import hashlib
import json
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
TARGET = 'tools/session-usage.py'
TEST = 'tests/test_session_usage.py'
MODELS = ('gpt-6.1-terra', 'gpt-6.1-sol')
PROVIDER_MODELS = {'codex': MODELS, 'claude': ('claude-sonnet-5-5', 'claude-opus-5-5')}
INSTRUCTION_FILES = {'codex': 'AGENTS.md', 'claude': 'CLAUDE.md'}
NOTICE = ('Seeded smoke benchmark, not a measure of real task quality. '
          'API token prices are not billed cost; no monetary estimate is calculated.')
# Every replacement changes one line and is checked against the untouched suite.
MUTATIONS = (
    ('token-total', 'Total tokens must count input and output once.',
     'result["total_tokens"] = result["input_tokens"] + result["output_tokens"]',
     'result["total_tokens"] = result["input_tokens"] + result["output_tokens"] + result["cached_input_tokens"]'),
    ('agent-window', 'Child responses must be selected within the requested time range.',
     'elif not start <= item["when"] <= end:', 'elif start <= item["when"] <= end:'),
    ('automatic-exclusion', 'Automatic approval agents must be excluded by default and included on request.',
     'elif agent["kind"] == "automatic" and not include_automatic:',
     'elif agent["kind"] == "automatic" and include_automatic:'),
    ('latest-response', 'Conflicting response records must use the latest timestamp.',
     'if previous["when"] > when:', 'if previous["when"] < when:'),
    ('overlapping-pauses', 'Overlapping pauses must be counted once after clipping to the selected range.',
     'paused = union_seconds(intervals)',
     'paused = sum((b - a).total_seconds() for a, b in intervals)'),
)


def execute(command, cwd, timeout, stdout, stderr):
    """Capture directly to files and kill descendants as well as the CLI on timeout."""
    started = time.monotonic()
    result = {'exit_code': None, 'timed_out': False, 'error': None}
    with stdout.open('wb') as out, stderr.open('wb') as err:
        try:
            process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                       start_new_session=True)
            try:
                result['exit_code'] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                result['timed_out'] = True
                os.killpg(process.pid, signal.SIGKILL)
                result['exit_code'] = process.wait()
        except OSError as error:
            result['error'] = str(error)
    result['duration_seconds'] = round(time.monotonic() - started, 3)
    return result


def populate(directory, source, tests, instructions, instruction_file='AGENTS.md'):
    for name, data in ((TARGET, source), (TEST, tests), (instruction_file, instructions)):
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def snapshot(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        if any(part in ('__pycache__', '.pytest_cache') for part in path.relative_to(directory).parts):
            continue
        name = str(path.relative_to(directory))
        if path.is_symlink():
            result[name] = 'symlink:' + os.readlink(path)
        elif path.is_file():
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def evaluate(source, tests, artifact):
    # A separate host-created tree prevents edited tests and extra modules from influencing scoring.
    with tempfile.TemporaryDirectory(prefix='fixer-evaluator-') as temporary:
        directory = Path(temporary)
        populate(directory, source, tests, b'')
        return execute([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                       directory, 30, artifact.with_suffix('.stdout.log'), artifact.with_suffix('.stderr.log'))


def event_usage(path):
    usage, errors = [], []
    for line in path.read_text(errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get('type') == 'turn.completed' and isinstance(event.get('usage'), dict):
            usage.append(event['usage'])
        if event.get('type') in ('error', 'turn.failed'):
            errors.append(event)
    return usage, errors


def claude_usage(path):
    """Parse defensively: use the final stream-json result event, if any."""
    usage, errors = [], []
    results = 0
    for line in path.read_text(errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or event.get('type') != 'result':
            continue
        results += 1
        if event.get('is_error') is not False:
            errors.append(event)
        if isinstance(event.get('usage'), dict):
            usage.append(event['usage'])
    if not results:
        errors.append({'type': 'missing_result_event'})
    return usage, errors


def run_model(model, task, source, tests, instructions, artifact, timeout, provider='codex'):
    artifact.mkdir()
    with tempfile.TemporaryDirectory(prefix='fixer-task-') as temporary:
        directory = Path(temporary)
        instruction_file = INSTRUCTION_FILES[provider]
        populate(directory, source, tests, instructions, instruction_file)
        before = snapshot(directory)
        prompt = (f'Fix the regression in {TARGET}. {task[1]} '
                  f'Run the existing {TEST} suite. Edit only {TARGET}; do not edit tests or {instruction_file}. '
                  'Work directly without delegation or subagents. Report the fix and validation.')
        if provider == 'claude':
            command = ['claude', '-p', prompt, '--model', model, '--effort', 'medium',
                       '--output-format', 'stream-json', '--verbose', '--no-session-persistence',
                       '--setting-sources', 'project', '--disable-slash-commands',
                       '--permission-mode', 'acceptEdits',
                       '--tools', 'Read,Edit,Write,Glob,Grep,Bash',
                       '--allowedTools', 'Read,Edit,Write,Glob,Grep,Bash(python3 *)',
                       '--disallowedTools', 'Agent']
        else:
            command = ['codex', 'exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
                       '--sandbox', 'workspace-write', '--json', '-m', model,
                       '-c', 'model_reasoning_effort="medium"', '-C', str(directory), prompt]
        result = execute(command, directory, timeout, artifact / 'events.jsonl', artifact / 'stderr.log')
        after = snapshot(directory)
        changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
        result.update(provider=provider, model=model, task=task[0], changed_files=changed,
                      outside_scope=[name for name in changed if name != TARGET])
        usage, errors = (claude_usage if provider == 'claude' else event_usage)(artifact / 'events.jsonl')
        result.update(usage=usage, event_errors=errors)
        target = directory / TARGET
        safe_target = target.is_file() and not target.is_symlink() and not target.parent.is_symlink()
        final = target.read_bytes() if safe_target else b''
        (artifact / 'final.py').write_bytes(final)
        patch = difflib.unified_diff(source.decode().splitlines(True), final.decode(errors='replace').splitlines(True),
                                     fromfile='before/' + TARGET, tofile='after/' + TARGET)
        (artifact / 'final.patch').write_text(''.join(patch))
        result['evaluator'] = evaluate(final, tests, artifact / 'evaluator')
        if result['error'] or result['timed_out'] or result['exit_code'] != 0 or errors or not usage:
            result['status'] = 'infrastructure_error'
        elif result['evaluator']['error']:
            result['status'] = 'infrastructure_error'
        else:
            result['status'] = ('passed' if safe_target and not result['outside_scope']
                                and not result['evaluator']['timed_out']
                                and result['evaluator']['exit_code'] == 0 else 'code_failure')
        (artifact / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=sorted(PROVIDER_MODELS), default='codex')
    parser.add_argument('--limit', type=int, choices=range(1, 6), default=5)
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('--output', type=Path, help='new output directory outside this repository (default: temporary directory)')
    parser.add_argument('--dry-run', action='store_true', help='validate baseline and all five mutations without model calls')
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    if args.output:
        output = args.output.expanduser().resolve()
        if output.is_relative_to(ROOT):
            parser.error('--output must be outside the repository')
        output.mkdir(parents=True, exist_ok=False)
    else:
        output = Path(tempfile.mkdtemp(prefix='fixer-benchmark-'))
    print(f'Artifacts: {output}', flush=True)
    source, tests = (ROOT / TARGET).read_bytes(), (ROOT / TEST).read_bytes()
    if args.provider == 'claude':
        body = re.sub(r'\A---\n.*?\n---\n', '', (ROOT / 'claude/fixer.md').read_text(), count=1, flags=re.S).lstrip('\n')
    else:
        body = re.search(r'(?ms)^developer_instructions\s*=\s*"""\n(.*?)^"""',
                         (ROOT / 'codex/fixer.toml').read_text()).group(1)
    instructions = (body + '\nWork directly. Do not delegate or spawn subagents.\n').encode()
    models = PROVIDER_MODELS[args.provider]
    summary = {'notice': NOTICE, 'provider': args.provider, 'effort': 'medium', 'dry_run': args.dry_run, 'validation': [], 'runs': []}
    baseline = evaluate(source, tests, output / 'baseline')
    summary['baseline'] = baseline
    valid = baseline['exit_code'] == 0 and not baseline['error'] and not baseline['timed_out']
    mutated = []
    for task in MUTATIONS:
        old, new = task[2].encode(), task[3].encode()
        if source.count(old) != 1:
            summary['validation'].append({'task': task[0], 'error': 'mutation anchor must occur exactly once'})
            valid = False
            continue
        candidate = source.replace(old, new)
        check = evaluate(candidate, tests, output / ('seed-' + task[0]))
        detected = check['exit_code'] == 1 and not check['error'] and not check['timed_out']
        summary['validation'].append({'task': task[0], 'detected': detected, **check})
        valid = valid and detected
        mutated.append((task, candidate))
    if valid and not args.dry_run:
        for index, (task, candidate) in enumerate(mutated[:args.limit]):
            for model in models[::1 if index % 2 == 0 else -1]:
                print(f'{task[0]}: {model}', flush=True)
                summary['runs'].append(run_model(model, task, candidate, tests, instructions,
                                                 output / f'{index + 1}-{task[0]}-{model}', args.timeout,
                                                 provider=args.provider))
    summary['infrastructure_failure'] = not valid or any(r['status'] == 'infrastructure_error' for r in summary['runs'])
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    source_event = 'result event' if args.provider == 'claude' else 'turn.completed'
    lines = [NOTICE, '', f'Seed validation: {"passed" if valid else "FAILED"}', '',
             f'| Task | Model | Status | Seconds | Usage from {source_event} |', '| --- | --- | --- | ---: | --- |']
    for run in summary['runs']:
        lines.append(f"| {run['task']} | {run['model']} | {run['status']} | {run['duration_seconds']} | {json.dumps(run['usage'])} |")
    (output / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(NOTICE)
    print(f'Summary: {output / "summary.md"}')
    return 2 if summary['infrastructure_failure'] else 0


if __name__ == '__main__':
    sys.exit(main())
