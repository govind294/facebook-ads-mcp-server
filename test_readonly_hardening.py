"""Synthetic regressions for read-only transport; no requests or MCP dependency."""
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class RequestException(Exception):
    pass


class FakeMCP:
    def __init__(self, *args, **kwargs):
        pass
    def tool(self):
        return lambda function: function
    def run(self, **kwargs):
        raise AssertionError('MCP runtime must not start in tests')


class Response:
    def __init__(self, data=None, status=200, error=None):
        self.data, self.status_code, self.error = data, status, error
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RequestException(self.error or 'unsafe token-bearing HTTP error')
    def json(self):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


mcp_module = types.ModuleType('mcp.server.fastmcp')
mcp_module.FastMCP = FakeMCP
requests_module = types.ModuleType('requests')
requests_module.exceptions = types.SimpleNamespace(RequestException=RequestException)
def forbidden(*args, **kwargs):
    raise AssertionError('Network must be mocked')
requests_module.get = forbidden
with patch.dict(sys.modules, {'mcp': types.ModuleType('mcp'), 'mcp.server': types.ModuleType('mcp.server'),
                              'mcp.server.fastmcp': mcp_module, 'requests': requests_module}):
    spec = importlib.util.spec_from_file_location('tested_server', Path(__file__).with_name('server.py'))
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)


def next_url(cursor, token='DUMMY_TOKEN'):
    return 'https://graph.facebook.com/v22.0/user/adaccounts?after=' + cursor + '&access_token=' + token


def first_page(rows, cursor=None):
    edge = {'data': rows, 'summary': {'total_count': 2}}
    if cursor:
        edge['paging'] = {'next': next_url(cursor), 'cursors': {'after': cursor}}
    return {'id': 'SYNTHETIC_USER', 'adaccounts': edge}


class ReadOnlyHardeningTests(unittest.TestCase):
    def setUp(self):
        server.FB_ACCESS_TOKEN = None
        self.env = patch.dict(os.environ, {'FB_ACCESS_TOKEN': 'ENV_DUMMY_TOKEN'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_environment_precedes_legacy_argv_and_no_stdout(self):
        stream = StringIO()
        with patch.object(sys, 'argv', ['server.py', '--fb-token', 'ARGV_DUMMY']), redirect_stdout(stream):
            self.assertEqual(server._get_fb_access_token(), 'ENV_DUMMY_TOKEN')
        self.assertEqual(stream.getvalue(), '')

    def test_legacy_argv_is_supported_without_environment(self):
        with patch.dict(os.environ, {'FB_ACCESS_TOKEN': ''}), patch.object(sys, 'argv', ['server.py', '--fb-token', 'ARGV_DUMMY']):
            self.assertEqual(server._get_fb_access_token(), 'ARGV_DUMMY')

    def test_missing_or_flag_like_argv_is_rejected(self):
        for args in (['server.py'], ['server.py', '--fb-token'], ['server.py', '--fb-token', '--other']):
            server.FB_ACCESS_TOKEN = None
            with self.subTest(args=args), patch.dict(os.environ, {'FB_ACCESS_TOKEN': ''}), patch.object(sys, 'argv', args), self.assertRaises(ValueError):
                server._get_fb_access_token()

    def test_nested_accounts_are_exhausted_and_exact_duplicates_deduplicated(self):
        a, b = {'id': 'act_A', 'name': 'A'}, {'id': 'act_B', 'name': 'B'}
        responses = [Response(first_page([a], 'one')), Response({'data': [], 'paging': {'next': next_url('two')}}), Response({'data': [a, b]})]
        with patch.object(server.requests, 'get', side_effect=responses) as get:
            result = server.list_ad_accounts()
        self.assertEqual(get.call_count, 3)
        self.assertEqual(result['id'], 'SYNTHETIC_USER')
        self.assertEqual(result['adaccounts']['data'], [a, b])
        self.assertEqual(result['adaccounts']['summary'], {'total_count': 2})
        self.assertNotIn('paging', result['adaccounts'])
        self.assertEqual(result['_collection'], {'pagination_complete': True, 'pages_fetched': 3, 'unique_accounts': 2})
        for call in get.call_args_list:
            self.assertEqual(call.kwargs['timeout'], 30)
            self.assertFalse(call.kwargs['allow_redirects'])

    def test_actual_empty_inventory_is_complete(self):
        with patch.object(server.requests, 'get', return_value=Response(first_page([]))):
            result = server.list_ad_accounts()
        self.assertEqual(result['adaccounts']['data'], [])
        self.assertTrue(result['_collection']['pagination_complete'])

    def test_page_limit_fails_instead_of_partial_complete(self):
        with patch.object(server.requests, 'get', return_value=Response(first_page([{'id': 'A'}], 'one'))) as get:
            with self.assertRaisesRegex(ValueError, 'max_pages reached'):
                server.list_ad_accounts(max_pages=1)
        self.assertEqual(get.call_count, 1)
        for limit in (0, -1, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                server.list_ad_accounts(max_pages=limit)

    def test_cursor_cycle_with_different_url_tokens_fails(self):
        responses = [Response(first_page([{'id': 'A'}], 'one')), Response({'data': [{'id': 'B'}], 'paging': {'next': next_url('one', 'OTHER_DUMMY')}})]
        with patch.object(server.requests, 'get', side_effect=responses) as get:
            with self.assertRaisesRegex(ValueError, 'Repeated pagination'):
                server.list_ad_accounts()
        self.assertEqual(get.call_count, 2)

    def test_conflicting_duplicate_id_fails(self):
        responses = [Response(first_page([{'id': 'A', 'name': 'old'}], 'one')), Response({'data': [{'id': 'A', 'name': 'new'}]})]
        with patch.object(server.requests, 'get', side_effect=responses), self.assertRaisesRegex(ValueError, 'Conflicting account'):
            server.list_ad_accounts()

    def test_malformed_page_or_account_fails(self):
        for data in ({}, {'adaccounts': {'data': {}}}, first_page([{'name': 'missing id'}]), first_page([1])):
            with self.subTest(data=data), patch.object(server.requests, 'get', return_value=Response(data)), self.assertRaises(ValueError):
                server.list_ad_accounts()

    def test_invalid_graph_targets_never_send_any_request(self):
        urls = ['http://graph.facebook.com/x', 'https://graph.facebook.com.evil.test/x',
                'https://user:DUMMY@graph.facebook.com/x', 'https://graph.facebook.com:444/x',
                'https://graph.facebook.com/x#fragment', 'https://graph.facebook.com/x\n',
                'https://graph.facebook.com:bad/x']
        with patch.object(server.requests, 'get') as get:
            for url in urls:
                with self.subTest(url=url), self.assertRaises(ValueError):
                    server.fetch_pagination_url(url)
            get.assert_not_called()

    def test_untrusted_next_url_is_rejected_before_second_request(self):
        data = first_page([{'id': 'A'}])
        data['adaccounts']['paging'] = {'next': 'https://evil.test/?access_token=DUMMY'}
        with patch.object(server.requests, 'get', return_value=Response(data)) as get:
            with self.assertRaises(ValueError):
                server.list_ad_accounts()
        self.assertEqual(get.call_count, 1)

    def test_regular_get_failure_never_emits_token_or_raw_url(self):
        raw = 'HTTPS failed https://graph.facebook.com/x?access_token=DUMMY%2FSECRET raw DUMMY/SECRET'
        stream = StringIO()
        with patch.object(server.requests, 'get', side_effect=RequestException(raw)), redirect_stdout(stream):
            with self.assertRaises(RequestException) as caught:
                server._make_graph_api_call('https://graph.facebook.com/x', {'access_token': 'DUMMY/SECRET'})
        self.assertEqual(str(caught.exception), 'Facebook Graph API request failed')
        self.assertNotIn('DUMMY', str(caught.exception) + stream.getvalue())
        self.assertTrue(caught.exception.__suppress_context__)

    def test_pagination_http_error_is_sanitized(self):
        response = Response(status=400, error='request access_token=DUMMY_TOKEN')
        stream = StringIO()
        with patch.object(server.requests, 'get', return_value=response) as get, redirect_stdout(stream):
            with self.assertRaises(RequestException) as caught:
                server.fetch_pagination_url(next_url('one'))
        self.assertEqual(str(caught.exception), 'Facebook Graph API request failed (HTTP 400)')
        self.assertEqual(stream.getvalue(), '')
        self.assertNotIn('DUMMY_TOKEN', str(caught.exception))
        self.assertEqual(get.call_args.kwargs, {'params': {}, 'allow_redirects': False, 'timeout': 30})

    def test_redirects_are_rejected_without_following(self):
        with patch.object(server.requests, 'get', return_value=Response({}, status=302)) as get:
            with self.assertRaisesRegex(RequestException, 'HTTP 302'):
                server.fetch_pagination_url(next_url('one'))
        self.assertFalse(get.call_args.kwargs['allow_redirects'])

    def test_bad_json_and_api_errors_are_not_empty_success(self):
        for data in (ValueError('DUMMY secret body'), [], {'error': {'message': 'DUMMY secret'}}):
            with self.subTest(data=data), patch.object(server.requests, 'get', return_value=Response(data)):
                with self.assertRaises(ValueError) as caught:
                    server._make_graph_api_call('https://graph.facebook.com/x', {})
                self.assertNotIn('DUMMY', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
