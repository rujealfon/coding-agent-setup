from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'tools/session-usage.py'
spec = importlib.util.spec_from_file_location('session_usage', CLI)
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)


def row(kind, payload, second=0):
    return {'type': kind, 'timestamp': f'2026-10-20T10:00:{second:02d}Z', 'payload': payload}


def meta(identity='root', parent=None, automatic=False):
    data = {'id': identity, 'session_id': 'root', 'cwd': '/example/project', 'timestamp': '2026-10-20T10:00:00Z'}
    if automatic:
        data.update(thread_source='guardian_review', source={'subagent': {'other': 'guardian'}})
    elif parent:
        data['source'] = {'subagent': {'thread_spawn': {'parent_thread_id': parent, 'agent_path': '/root/' + identity, 'agent_role': 'fixer'}}}
    return row('session_meta', data)


def boundary(turn, kind, second):
    return row('event_msg', {'type': kind, 'turn_id': turn}, second)


def context(turn='t1', model='sol', effort='medium'):
    return row('turn_context', {'turn_id': turn, 'model': model, 'effort': effort})


def response(identity='root', turn='t1', response_id='r1', second=2, count=100):
    return row('token_usage_record', {'thread_id': identity, 'session_id': 'root', 'turn_id': turn,
        'response_id': response_id, 'usage': {'input_tokens': count, 'cached_input_tokens': 80,
        'output_tokens': 20, 'reasoning_output_tokens': 7, 'total_tokens': count + 20},
        'thread_token_usage': {'input_tokens': 999999}}, second)


class UsageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.root = [meta(), context(), boundary('t1', 'task_started', 0), response(), boundary('t1', 'task_complete', 10),
                     context('t2'), boundary('t2', 'task_started', 20), response(turn='t2', response_id='r2', second=22),
                     boundary('t2', 'task_complete', 30)]

    def write(self, name, rows):
        path = self.directory / name
        path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        return path

    def loaded(self):
        warnings = set()
        return usage.load_session(usage.inventory(self.directory, warnings), 'root', warnings), warnings

    def report(self, first='t1', last='t1', exclude=(), automatic=False, pauses=()):
        loaded, warnings = self.loaded()
        return usage.report(loaded, 'root', first, last, exclude, automatic, pauses, warnings)

    def test_response_deduplication_does_not_sum_cumulative_or_reasoning_twice(self):
        self.write('root.jsonl', self.root + [response(), row('event_msg', {'type': 'token_count', 'info': {'total_token_usage': {'total_tokens': 999999}}})])
        result = self.report()
        self.assertEqual(result['totals']['total_tokens'], 120)
        self.assertEqual(result['totals']['uncached_input_tokens'], 20)
        self.assertEqual(result['totals']['reasoning_output_tokens'], 7)
        self.assertEqual(result['accounting']['responses'], 1)

    def test_fork_inherited_metadata_does_not_replace_child_identity(self):
        self.write('root.jsonl', self.root)
        self.write('child.jsonl', [meta('child', 'root'), meta(), context('ct'), response('child', 'ct', 'c1', 3)])
        result = self.report()
        self.assertEqual(result['totals']['total_tokens'], 240)
        child = next(a for a in result['agents'] if a['thread_id'] == 'child')
        self.assertEqual(child['agent'], '/root/child')

    def test_nested_preexisting_agent_followups_selected_by_response_time(self):
        self.write('root.jsonl', self.root)
        self.write('child.jsonl', [meta('child', 'root'), context('ct'), response('child', 'ct', 'c1', 1), response('child', 'ct', 'c2', 25)])
        self.write('nested.jsonl', [meta('nested', 'child'), context('nt'), response('nested', 'nt', 'n1', 24)])
        result = self.report('t2', 't2')
        self.assertEqual(result['totals']['total_tokens'], 360)
        self.assertEqual(result['accounting']['responses'], 3)

    def test_automatic_and_explicit_exclusions_are_visible(self):
        self.write('root.jsonl', self.root)
        self.write('guard.jsonl', [meta('guard', automatic=True), context('gt'), response('guard', 'gt', 'g1', 4)])
        self.write('child.jsonl', [meta('child', 'root'), context('ct'), response('child', 'ct', 'c1', 4)])
        result = self.report(exclude=['/root/child'])
        self.assertEqual(result['totals']['total_tokens'], 120)
        self.assertEqual(len(result['excluded']), 2)
        self.assertEqual(self.report(automatic=True)['totals']['total_tokens'], 360)

    def test_conflicting_response_uses_latest_and_warns(self):
        self.write('root.jsonl', self.root + [response(second=4, count=200)])
        result = self.report()
        self.assertEqual(result['totals']['input_tokens'], 200)
        self.assertTrue(any('Conflicting' in w for w in result['warnings']))

    def test_malformed_record_warns_without_echoing_contents(self):
        path = self.write('root.jsonl', self.root)
        with path.open('a') as stream:
            stream.write('{PRIVATE_SECRET\n')
        result = self.report()
        self.assertTrue(any('unreadable JSON' in w for w in result['warnings']))
        self.assertNotIn('PRIVATE_SECRET', json.dumps(result))
        self.assertFalse(result['accounting']['complete'])

    def test_cumulative_only_usage_is_unknown(self):
        self.write('root.jsonl', [meta(), boundary('t1', 'task_started', 0), row('event_msg', {'type': 'token_count'}), boundary('t1', 'task_complete', 10)])
        result = self.report()
        self.assertIsNone(result['totals'])
        self.assertFalse(result['accounting']['complete'])
        self.assertTrue(any('unknown, not zero' in w for w in result['warnings']))

    def test_invalid_and_missing_usage_are_not_zero_usage(self):
        bad = response(response_id='bad')
        bad['payload']['usage']['cached_input_tokens'] = 500
        missing = response(response_id='missing')
        missing['payload']['usage'] = None
        self.write('root.jsonl', self.root + [bad, missing])
        result = self.report()
        self.assertEqual(result['accounting']['invalid_usage_records_in_session'], 2)
        self.assertFalse(result['accounting']['complete'])
        self.assertEqual(result['totals']['total_tokens'], 120)

    def test_unknown_model_and_effort_remain_unknown(self):
        self.write('root.jsonl', [r for r in self.root if r['type'] != 'turn_context'])
        result = self.report()
        self.assertIsNone(result['agents'][0]['model'])
        self.assertTrue(any('unknown model' in w for w in result['warnings']))

    def test_incomplete_turn_ends_at_last_root_usage(self):
        self.write('root.jsonl', self.root[:-1])
        result = self.report('t2', 't2')
        self.assertEqual(result['timing']['elapsed_seconds'], 2)
        self.assertTrue(any('incomplete' in w for w in result['warnings']))

    def test_pauses_are_clipped_merged_and_do_not_remove_usage(self):
        self.write('root.jsonl', self.root)
        result = self.report(pauses=['2026-10-20T09:59:59Z/2026-10-20T10:00:04Z',
                                     '2026-10-20T10:00:02Z/2026-10-20T10:00:06Z'])
        self.assertEqual(result['timing']['excluded_pause_seconds'], 6)
        self.assertEqual(result['timing']['elapsed_without_pauses_seconds'], 4)
        self.assertEqual(result['totals']['total_tokens'], 120)

    def test_invalid_boundaries_fail_instead_of_guessing(self):
        self.write('root.jsonl', self.root)
        for first, last in [('absent', 't1'), ('t2', 't1')]:
            with self.subTest(first=first), self.assertRaises(ValueError):
                self.report(first, last)
        with self.assertRaises(ValueError):
            self.report(pauses=['not-a-range'])

    def test_unrelated_sessions_do_not_contribute_usage(self):
        self.write('root.jsonl', self.root)
        other = meta('other')
        other['payload']['session_id'] = 'other'
        self.write('other.jsonl', [other, response('other', response_id='other')])
        self.assertEqual(self.report()['totals']['total_tokens'], 120)

    def test_outputs_do_not_export_conversation_or_tool_results(self):
        self.write('root.jsonl', self.root + [row('response_item', {'role': 'user', 'content': [{'text': 'PRIVATE_PROMPT'}]}),
                                            row('response_item', {'type': 'function_call_output', 'output': 'PRIVATE_TOOL'})])
        data = self.report()
        for rendered in [json.dumps(data), usage.markdown(data)]:
            self.assertNotIn('PRIVATE_PROMPT', rendered)
            self.assertNotIn('PRIVATE_TOOL', rendered)

    def test_list_filters_directory_and_omits_children(self):
        self.write('root.jsonl', self.root)
        self.write('child.jsonl', [meta('child', 'root')])
        output = io.StringIO()
        with redirect_stdout(output):
            code = usage.main(['--sessions-dir', str(self.directory), 'list', '--cwd', '/example/project', '--format', 'json'])
        self.assertEqual(code, 0)
        self.assertEqual([s['session_id'] for s in json.loads(output.getvalue())['sessions']], ['root'])

    def test_cli_turns_and_report_json_and_missing_session_exit(self):
        self.write('root.jsonl', self.root)
        for command in ['turns', 'report']:
            result = subprocess.run([sys.executable, '-B', str(CLI), '--sessions-dir', str(self.directory), command,
                                     '--session', 'root', '--format', 'json'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['session_id'], 'root')
        result = subprocess.run([sys.executable, '-B', str(CLI), '--sessions-dir', str(self.directory), 'report',
                                 '--session', 'missing'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('root session not found', result.stderr)

    def test_metadata_only_child_has_unknown_usage(self):
        self.write('root.jsonl', self.root)
        self.write('child.jsonl', [meta('child', 'root'), context('ct')])
        result = self.report()
        self.assertFalse(result['accounting']['complete'])
        self.assertEqual(result['unaccounted'][0]['agent'], '/root/child')
        self.assertEqual(result['totals']['total_tokens'], 120)
        self.assertTrue(self.report(exclude=['/root/child'])['accounting']['complete'])

    def test_selected_root_turn_without_response_is_unknown(self):
        self.write('root.jsonl', [r for r in self.root if not (r['type'] == 'token_usage_record' and r['payload']['turn_id'] == 't2')])
        result = self.report('t1', 't2')
        self.assertFalse(result['accounting']['complete'])
        self.assertEqual(result['unaccounted'][0]['turn_id'], 't2')

    def test_reused_child_activity_without_usage_is_unknown(self):
        self.write('root.jsonl', self.root)
        self.write('child.jsonl', [meta('child', 'root'), context('ct'), response('child', 'ct', 'c1', 2),
                                   boundary('ct2', 'task_started', 21)])
        result = self.report('t2', 't2')
        self.assertFalse(result['accounting']['complete'])
        self.assertEqual(result['unaccounted'][0]['agent'], '/root/child')

    def test_one_known_child_turn_does_not_hide_another_missing_turn(self):
        self.write('root.jsonl', self.root)
        self.write('child.jsonl', [meta('child', 'root'), context('ct'), response('child', 'ct', 'c1', 2),
                                   boundary('ct2', 'task_started', 5)])
        result = self.report()
        self.assertFalse(result['accounting']['complete'])
        self.assertEqual(result['unaccounted'][0]['turn_id'], 'ct2')

    def test_restamped_inherited_parent_activity_is_not_missing_child_usage(self):
        self.write('root.jsonl', self.root)
        self.write('child.jsonl', [meta('child', 'root'), boundary('t1', 'task_started', 1),
                                   context('ct'), response('child', 'ct', 'c1', 3)])
        result = self.report()
        self.assertTrue(result['accounting']['complete'])
        self.assertEqual(result['unaccounted'], [])

    def test_model_changes_within_turn_are_reported_separately(self):
        self.write('root.jsonl', self.root + [context(model='astra', effort='high'), response(response_id='new', second=5)])
        result = self.report()
        self.assertEqual({a['model'] for a in result['agents']}, {'sol', 'astra'})

    def test_pause_requires_timezone_and_order(self):
        self.write('root.jsonl', self.root)
        for pause in ['2026-10-20T10:00:00/2026-10-20T10:00:05',
                      '2026-10-20T10:00:05Z/2026-10-20T10:00:00Z']:
            with self.subTest(pause=pause), self.assertRaises(ValueError):
                self.report(pauses=[pause])

    def test_markdown_escapes_agent_label_cells(self):
        self.write('root.jsonl', self.root)
        data = self.report()
        data['agents'][0]['agent'] = 'agent|name\nnext'
        self.assertIn('agent\\|name next', usage.markdown(data))


if __name__ == '__main__':
    unittest.main()
