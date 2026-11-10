import hashlib
import hmac
import importlib.util
import inspect
import json
import unittest


def feature(test, module, function):
    spec = importlib.util.find_spec(module)
    test.assertIsNotNone(spec, f"Missing {module}: GTM feature not implemented")
    loaded = __import__(module)
    fn = getattr(loaded, function, None)
    test.assertTrue(callable(fn), f"Missing {module}.{function}")
    return fn


class SlackBoundaryTests(unittest.TestCase):
    def verify(self):
        return feature(self, "slack_logic", "verify_signature")

    def test_raw_body_signature_and_five_minute_boundary(self):
        raw = b'team_id=TDEMO&text=hello%20world'
        sig = 'v0=' + hmac.new(b'secret', b'v0:1000:' + raw, hashlib.sha256).hexdigest()
        self.assertTrue(self.verify()(raw, {'x-slack-request-timestamp': '1000', 'x-slack-signature': sig}, 'secret', 1300))
        self.assertFalse(self.verify()(raw, {'x-slack-request-timestamp': '1000', 'x-slack-signature': sig}, 'secret', 1301))
        self.assertFalse(self.verify()(raw + b'!', {'x-slack-request-timestamp': '1000', 'x-slack-signature': sig}, 'secret', 1000))
        self.assertFalse(self.verify()(raw, {}, 'secret', 1000))

    def test_slash_command_routes_skill_and_preserves_actor(self):
        parse = feature(self, 'slack_logic', 'parse_command')
        result = parse({'team_id': 'TDEMO', 'user_id': 'UROHAN', 'channel_id': 'CDEMO',
                        'trigger_id': '123.45', 'command': '/gtm',
                        'text': 'call-review demo-001 | stage is Proposal'}, 'TDEMO', ['UROHAN'])
        self.assertEqual(result['skill_id'], 'call-review')
        self.assertEqual(result['input'], 'stage is Proposal')
        self.assertEqual(result['actor'], {'team_id': 'TDEMO', 'user_id': 'UROHAN', 'credential_mode': 'service_role'})
        self.assertEqual(result['opportunity_id'], 'demo-001')
        self.assertEqual(result['request_id'], 'slack-123-45')

    def test_other_workspace_user_unknown_skill_and_real_ids_rejected(self):
        parse = feature(self, 'slack_logic', 'parse_command')
        base = {'team_id': 'TDEMO', 'user_id': 'UROHAN', 'channel_id': 'CDEMO', 'trigger_id': '1',
                'command': '/gtm', 'text': 'meeting-prep demo-001'}
        for change in [{'team_id': 'TOTHER'}, {'user_id': 'UOTHER'}, {'text': 'shell demo-001'},
                       {'text': 'call-review real-opportunity | stage is Proposal'}, {'text': 'call-review demo-001'}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                parse({**base, **change}, 'TDEMO', ['UROHAN'])

    def test_directory_lists_only_users_skills_and_denies_hidden_workflow(self):
        parse = feature(self, 'slack_logic', 'parse_command')
        self.assertGreaterEqual(len(inspect.signature(parse).parameters), 4, 'User skill grants not implemented')
        form = {'team_id': 'TDEMO', 'user_id': 'UROHAN', 'channel_id': 'CDEMO', 'trigger_id': '1', 'command': '/gtm', 'text': 'skills'}
        got = parse(form, 'TDEMO', ['UROHAN'], {'UROHAN': ['meeting-prep']})
        self.assertEqual(got['permitted_skills'], ['meeting-prep'])
        self.assertEqual(got['kind'], 'skill_directory')
        with self.assertRaises(ValueError):
            parse({**form, 'text': 'call-review demo-1 | stage is Proposal'}, 'TDEMO', ['UROHAN'], {'UROHAN': ['meeting-prep']})

    def test_execution_grant_cannot_change_user_skill_or_target(self):
        sign = feature(self, 'execution_identity', 'sign_grant')
        verify = feature(self, 'execution_identity', 'verify_grant')
        grant = {'user_id': 'UROHAN', 'team_id': 'TDEMO', 'skill_id': 'meeting-prep', 'opportunity_id': 'demo-1',
                 'request_id': 'req', 'expires_at': 1500, 'allowed_tools': ['crm-tools___get_opportunity']}
        auth = sign(grant, 'secret')
        self.assertTrue(verify(auth, 'secret', 'get_opportunity', {'opportunity_id': 'demo-1'}, 1000))
        self.assertFalse(verify(auth, 'secret', 'commit_sales', {'opportunity_id': 'demo-1'}, 1000))
        self.assertFalse(verify(auth, 'secret', 'get_opportunity', {'opportunity_id': 'demo-2'}, 1000))
        self.assertFalse(verify(auth, 'secret', 'get_opportunity', {'opportunity_id': 'demo-1'}, 1501))
        auth['grant']['user_id'] = 'UADMIN'
        self.assertFalse(verify(auth, 'secret', 'get_opportunity', {'opportunity_id': 'demo-1'}, 1000))


class SkillTests(unittest.TestCase):
    def test_only_catalog_pinned_hash_and_approved_tool_are_loaded(self):
        load = feature(self, 'skill_catalog', 'load_skill')
        raw = b'Extract explicit sales facts.'
        catalog = {'release': 'demo-1', 'skills': {'call-review': {'version': '1.0.0',
            'key': 'skills/call-review/1.0.0/SKILL.md', 'sha256': hashlib.sha256(raw).hexdigest(),
            'allowed_tools': ['crm-tools___commit_sales', 'crm-tools___filter_findings']}}}
        got = load('call-review', catalog, lambda key: raw)
        self.assertEqual(got['instructions'], 'Extract explicit sales facts.')
        self.assertEqual(got['version'], '1.0.0')
        with self.assertRaises(ValueError):
            load('call-review', catalog, lambda key: b'tampered')
        with self.assertRaises(ValueError):
            load('unknown', catalog, lambda key: raw)
        catalog['skills']['call-review']['key'] = '../secret'
        with self.assertRaises(ValueError):
            load('call-review', catalog, lambda key: raw)

    def test_gtm_harness_consumes_skill_and_calls_only_gateway_tools(self):
        run = feature(self, 'gtm_logic', 'run_gtm')
        class Model:
            def __init__(self): self.calls = 0; self.system = ''
            def converse(self, **kw):
                self.system = kw['system'][0]['text']; self.calls += 1
                content = [{'toolUse': {'toolUseId': '1', 'name': 'submit_sales_updates', 'input': {'proposals': []}}}] if self.calls == 1 else [{'text': 'No updates'}]
                return {'output': {'message': {'role': 'assistant', 'content': content}}, 'usage': {}, 'stopReason': 'tool_use' if self.calls == 1 else 'end_turn'}
        model = Model(); calls = []
        def mcp(name, args):
            calls.append(name)
            return {'result': []} if name.endswith('filter_findings') else {'write_status': 'rejected', 'crm_fields': {}}
        skill = {'version': '1.0.0', 'release': 'demo-1', 'instructions': 'REVIEW_SKILL_LOADED',
                 'allowed_tools': ['crm-tools___filter_findings', 'crm-tools___commit_sales']}
        result = run({'skill_id': 'call-review', 'input': 'No facts', 'opportunity_id': 'demo-1', 'request_id': 'req'}, model, lambda name: skill, mcp)
        self.assertIn('REVIEW_SKILL_LOADED', model.system)
        self.assertEqual(calls, ['crm-tools___filter_findings', 'crm-tools___commit_sales'])
        self.assertEqual(result['skill_version'], '1.0.0')
        self.assertEqual(result['sales_result']['write_status'], 'rejected')
        skill['allowed_tools'] = []
        with self.assertRaises(ValueError):
            run({'skill_id': 'call-review', 'input': 'No facts', 'opportunity_id': 'demo-1', 'request_id': 'req2'}, Model(), lambda name: skill, mcp)

    def test_meeting_prep_uses_read_only_tool_and_reports_evidence(self):
        run = feature(self, 'gtm_logic', 'run_gtm')
        class Model:
            def converse(self, **kw):
                return {'output': {'message': {'content': [{'text': 'Prepare for proposal review.'}]}}, 'usage': {'inputTokens': 5, 'outputTokens': 4}}
        def mcp(name, args):
            self.assertEqual(name, 'crm-tools___get_opportunity')
            return {'opportunity_id': 'demo-1', 'crm_fields': {'stage': 'Proposal'}, 'event_count': 1}
        result = run({'skill_id': 'meeting-prep', 'input': '', 'opportunity_id': 'demo-1', 'request_id': 'prep'}, Model(),
                     lambda name: {'version': '1.0.0', 'release': 'demo-1', 'instructions': 'Use context', 'allowed_tools': ['crm-tools___get_opportunity']}, mcp)
        self.assertEqual(result['context']['crm_fields'], {'stage': 'Proposal'})
        self.assertEqual(result['status'], 'completed')


class AdapterTests(unittest.TestCase):
    def test_runtime_user_is_bound_to_verified_slack_actor(self):
        resolve = feature(self, 'slack_handlers', 'runtime_identity')
        secret = {'team_id': 'TDEMO', 'allowed_users': ['UROHAN'], 'skill_grants': {'UROHAN': ['meeting-prep']}}
        body = {'source': 'slack', 'skill_id': 'meeting-prep', 'actor': {'team_id': 'TDEMO', 'user_id': 'UROHAN'}}
        self.assertEqual(resolve(body, secret), ('slack:TDEMO:UROHAN', 'runtime_user'))
        self.assertEqual(resolve({'source': 'backend'}, secret), (None, 'service_workload'))
        for change in [{'skill_id': 'call-review'}, {'actor': {'team_id': 'TDEMO', 'user_id': 'UADMIN'}}]:
            with self.assertRaises(ValueError): resolve({**body, **change}, secret)

    def test_job_claim_uses_reserved_attribute_alias_and_sets_expiry(self):
        claim = feature(self, 'slack_handlers', 'claim_job')
        class Table:
            def update_item(self, **kw):
                self.kw = kw
                if kw.get('ExpressionAttributeNames', {}).get('#expiry') != 'ttl':
                    raise ValueError('DynamoDB ttl is a reserved word')
        table = Table()
        claim(table, {'request_id': 'req', 'input': 'hello'}, 1000)
        self.assertEqual(table.kw['Key'], {'request_id': 'req'})
        self.assertEqual(table.kw['ExpressionAttributeValues'][':ttl'], 87400)

    def test_gateway_dispatch_rejects_unregistered_tools_and_bounds_filter(self):
        dispatch = feature(self, 'gateway_tools', 'dispatch')
        self.assertEqual(dispatch('shell', {}, None), {'error': 'unknown_tool'})
        got = dispatch('filter_findings', {'findings': [{'score': 0.8, 'entity_group': 'stage'}, {'score': 0.7}], 'threshold': 0.8}, None)
        self.assertEqual(got['result'], [{'score': 0.8, 'entity_group': 'stage'}])
        with self.assertRaises(ValueError):
            dispatch('commit_sales', {'opportunity_id': 'real-1'}, None)

    def test_verified_webhook_queues_once_without_waiting_for_model(self):
        handle = feature(self, 'slack_handlers', 'process_webhook')
        body = b'team_id=TDEMO&user_id=UROHAN&channel_id=CDEMO&trigger_id=12.3&command=%2Fgtm&text=call-review+demo-001+%7C+stage+is+Proposal'
        sig = 'v0=' + hmac.new(b'secret', b'v0:1000:' + body, hashlib.sha256).hexdigest()
        event = {'body': body.decode(), 'headers': {'x-slack-request-timestamp': '1000', 'x-slack-signature': sig}, 'rawPath': '/slack/events'}
        queued = []
        secret = {'signing_secret': 'secret', 'team_id': 'TDEMO', 'allowed_users': ['UROHAN']}
        response = handle(event, secret, queued.append, 1000)
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0]['skill_id'], 'call-review')
        event['headers']['x-slack-signature'] = 'v0=wrong'
        self.assertEqual(handle(event, secret, queued.append, 1000)['statusCode'], 401)
        self.assertEqual(len(queued), 1)

    def test_queue_retry_reuses_saved_result_and_does_not_rerun_agent(self):
        execute = feature(self, 'slack_handlers', 'execute_job')
        payload = {'request_id': 'req', 'channel_id': 'CDEMO', 'source': 'slack', 'skill_id': 'call-review'}
        saved = []; posted = []
        result = {'status': 'completed', 'skill_version': '1.0.0', 'answer': 'Written',
                  'sales_result': {'write_status': 'written', 'crm_fields': {'stage': 'Proposal'}}}
        execute(payload, {'result': result}, lambda p: self.fail('Agent must not rerun'), saved.append, lambda p, r: posted.append(r) or '123.4')
        self.assertEqual(posted, [result])
        self.assertEqual(saved[-1]['slack_ts'], '123.4')
        execute(payload, {'result': result, 'slack_ts': '123.4'}, lambda p: self.fail('Agent must not rerun'), saved.append, lambda p, r: self.fail('Already delivered'))

    def test_mcp_response_can_decode_json_and_streamed_sse(self):
        decode = feature(self, 'gateway_client', 'decode_response')
        raw = {'jsonrpc': '2.0', 'id': 1, 'result': {'content': [{'type': 'text', 'text': '{"write_status":"written"}'}]}}
        self.assertEqual(decode(json.dumps(raw).encode())['result']['content'][0]['type'], 'text')
        self.assertEqual(decode(('event: message\ndata: ' + json.dumps(raw) + '\n\n').encode())['id'], 1)


if __name__ == '__main__':
    unittest.main()
