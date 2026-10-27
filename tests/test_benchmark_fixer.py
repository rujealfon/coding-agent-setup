import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch, Mock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('benchmark_fixer', ROOT / 'tools/benchmark-fixer.py')
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class BenchmarkTests(unittest.TestCase):
    def test_baseline_passes_and_every_single_line_seed_is_detected(self):
        source = (ROOT / benchmark.TARGET).read_bytes()
        tests = (ROOT / benchmark.TEST).read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.assertEqual(benchmark.evaluate(source, tests, directory / 'baseline')['exit_code'], 0)
            self.assertEqual(len(benchmark.MUTATIONS), 5)
            for task in benchmark.MUTATIONS:
                with self.subTest(task=task[0]):
                    old, new = task[2].encode(), task[3].encode()
                    self.assertEqual(source.count(old), 1)
                    self.assertNotIn(b'\n', old)
                    self.assertNotIn(b'\n', new)
                    mutated = source.replace(old, new)
                    compile(mutated, benchmark.TARGET, 'exec')
                    self.assertEqual(benchmark.evaluate(mutated, tests, directory / task[0])['exit_code'], 1)

    def model_run(self, edit_tests=False, extra_file=False, completed=True, exit_code=0, evaluator_result=None):
        tests = b'original trusted tests'
        def fake_execute(command, cwd, timeout, stdout, stderr):
            self.assertEqual(set(benchmark.snapshot(cwd)), {benchmark.TARGET, benchmark.TEST, 'AGENTS.md'})
            self.assertIn('--ignore-user-config', command)
            self.assertIn('--ephemeral', command)
            self.assertIn('model_reasoning_effort="medium"', command)
            self.assertNotIn(str(ROOT), ' '.join(command))
            (cwd / benchmark.TARGET).write_bytes(b'repaired\n')
            if edit_tests:
                (cwd / benchmark.TEST).write_bytes(b'cheating tests')
            if extra_file:
                (cwd / 'helper.py').write_bytes(b'pass\n')
            stdout.write_text(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 10}}) + '\n'
                              if completed else '')
            stderr.write_text('')
            return {'exit_code': exit_code, 'timed_out': False, 'error': None, 'duration_seconds': 1}
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(benchmark, 'execute', side_effect=fake_execute), patch.object(
                    benchmark, 'evaluate', return_value=evaluator_result or {
                        'exit_code': 0, 'timed_out': False, 'error': None}) as evaluator:
                artifact = Path(temporary) / 'run'
                result = benchmark.run_model('gpt-6.1-sol', benchmark.MUTATIONS[0], b'broken\n', tests,
                                             b'Do not delegate', artifact, 180)
                evaluator.assert_called_once_with(b'repaired\n', tests, artifact / 'evaluator')
                self.assertIn('-broken\n+repaired\n', (artifact / 'final.patch').read_text())
                self.assertEqual(json.loads((artifact / 'result.json').read_text()), result)
                return result

    def claude_run(self, events, exit_code=0):
        def fake_execute(command, cwd, timeout, stdout, stderr):
            self.assertEqual(set(benchmark.snapshot(cwd)), {benchmark.TARGET, benchmark.TEST, 'CLAUDE.md'})
            self.assertEqual(command[0], 'claude')
            self.assertEqual(command[command.index('--effort') + 1], 'medium')
            for flag in ('--no-session-persistence', '--disable-slash-commands', '--verbose'):
                self.assertIn(flag, command)
            self.assertEqual(command[command.index('--setting-sources') + 1], 'project')
            self.assertEqual(command[command.index('--permission-mode') + 1], 'acceptEdits')
            self.assertEqual(command[command.index('--tools') + 1], 'Read,Edit,Write,Glob,Grep,Bash')
            self.assertEqual(command[command.index('--disallowedTools') + 1], 'Agent')
            self.assertNotIn('--bare', command)
            self.assertIn('Bash(python3 *)', command[command.index('--allowedTools') + 1])
            self.assertIn('do not edit tests or CLAUDE.md', command[2])
            (cwd / benchmark.TARGET).write_bytes(b'repaired\n')
            stdout.write_text(''.join(json.dumps(event) + '\n' for event in events))
            stderr.write_text('')
            return {'exit_code': exit_code, 'timed_out': False, 'error': None, 'duration_seconds': 1}
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(benchmark, 'execute', side_effect=fake_execute), patch.object(
                    benchmark, 'evaluate', return_value={'exit_code': 0, 'timed_out': False, 'error': None}):
                return benchmark.run_model('claude-opus-5-5', benchmark.MUTATIONS[0], b'broken\n', b'tests',
                                           b'Do not delegate', Path(temporary) / 'run', 180, provider='claude')

    def test_claude_usage_comes_from_result_event(self):
        result = self.claude_run([{'type': 'assistant', 'usage': {'input_tokens': 1}},
                                  {'type': 'result', 'is_error': False, 'usage': {'input_tokens': 7}}])
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['usage'], [{'input_tokens': 7}])
        self.assertEqual(result['provider'], 'claude')

    def test_claude_error_or_missing_result_is_infrastructure_error(self):
        for events in ([{'type': 'result', 'is_error': True, 'usage': {'input_tokens': 7}}],
                       [{'type': 'assistant', 'usage': {'input_tokens': 1}}]):
            with self.subTest(events=events):
                self.assertEqual(self.claude_run(events)['status'], 'infrastructure_error')

    def test_claude_dry_run_never_starts_model_and_alternates_claude_models(self):
        models = benchmark.PROVIDER_MODELS['claude']
        self.assertEqual(models, ('claude-sonnet-5-5', 'claude-opus-5-5'))
        with tempfile.TemporaryDirectory() as temporary:
            for dry_run in (True, False):
                with self.subTest(dry_run=dry_run), patch.object(benchmark, 'evaluate', side_effect=[
                        {'exit_code': 0, 'error': None, 'timed_out': False}] + [
                        {'exit_code': 1, 'error': None, 'timed_out': False}] * 5), patch.object(
                        benchmark, 'run_model', return_value={'status': 'passed', 'task': 't',
                                                             'model': 'm', 'duration_seconds': 0, 'usage': []}) as run:
                    args = ['--provider', 'claude', '--output', str(Path(temporary) / str(dry_run)), '--limit', '2']
                    benchmark.main(args + (['--dry-run'] if dry_run else []))
                    summary = json.loads((Path(temporary) / str(dry_run) / 'summary.json').read_text())
                    self.assertEqual(summary['provider'], 'claude')
                    if dry_run:
                        run.assert_not_called()
                    else:
                        self.assertEqual([call.args[0] for call in run.call_args_list],
                                         [*models, *reversed(models)])
                        self.assertEqual({call.kwargs['provider'] for call in run.call_args_list}, {'claude'})

    def test_success_records_usage_and_patch(self):
        result = self.model_run()
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['usage'], [{'input_tokens': 10}])

    def test_edited_tests_and_extra_files_fail_even_when_evaluator_passes(self):
        for option, path in [('edit_tests', benchmark.TEST), ('extra_file', 'helper.py')]:
            with self.subTest(option=option):
                result = self.model_run(**{option: True})
                self.assertEqual(result['status'], 'code_failure')
                self.assertEqual(result['outside_scope'], [path])

    def test_missing_completion_or_cli_failure_is_infrastructure_error(self):
        for options in [{'completed': False}, {'exit_code': 1}]:
            with self.subTest(options=options):
                self.assertEqual(self.model_run(**options)['status'], 'infrastructure_error')

    def test_model_produced_evaluator_timeout_is_code_failure(self):
        result = self.model_run(evaluator_result={'exit_code': -9, 'timed_out': True, 'error': None})
        self.assertEqual(result['status'], 'code_failure')

    def test_timeout_kills_process_group_and_disables_stdin(self):
        process = Mock(pid=123)
        process.wait.side_effect = [subprocess.TimeoutExpired('codex', 180), -9]
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with patch.object(benchmark.subprocess, 'Popen', return_value=process) as popen, patch.object(
                    benchmark.os, 'killpg') as kill:
                result = benchmark.execute(['codex'], directory, 180, directory / 'out', directory / 'err')
                self.assertTrue(result['timed_out'])
                self.assertEqual(result['exit_code'], -9)
                self.assertEqual(popen.call_args.kwargs['stdin'], subprocess.DEVNULL)
                self.assertTrue(popen.call_args.kwargs['start_new_session'])
                kill.assert_called_once_with(123, benchmark.signal.SIGKILL)

    def test_dry_run_never_starts_model_and_alternates_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            for dry_run in (True, False):
                with self.subTest(dry_run=dry_run), patch.object(benchmark, 'evaluate', side_effect=[
                        {'exit_code': 0, 'error': None, 'timed_out': False}] + [
                        {'exit_code': 1, 'error': None, 'timed_out': False}] * 5), patch.object(
                        benchmark, 'run_model', return_value={'status': 'infrastructure_error', 'task': 't',
                                                             'model': 'm', 'duration_seconds': 0, 'usage': []}) as run:
                    args = ['--output', str(Path(temporary) / str(dry_run)), '--limit', '2']
                    code = benchmark.main(args + (['--dry-run'] if dry_run else []))
                    if dry_run:
                        run.assert_not_called()
                        self.assertEqual(code, 0)
                    else:
                        self.assertEqual([call.args[0] for call in run.call_args_list],
                                         [*benchmark.MODELS, *reversed(benchmark.MODELS)])
                        self.assertEqual(code, 2)


if __name__ == '__main__':
    unittest.main()
