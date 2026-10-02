import unittest
from services.cloud_reasoning import cloud_reasoning_profile, apply_cloud_reasoning, connection_reasoning_profile

class CloudReasoningTests(unittest.TestCase):
    def request(self, provider, model, value, url=''):
        body = {'temperature': .2, 'max_tokens': 4096, 'generationConfig': {}}
        apply_cloud_reasoning(body, {'selection_type': provider.removeprefix('custom:test') or ('groq' if 'groq' in url else 'alibaba'), 'base_url': url}, model, value)
        return body

    def test_user_stages_override_unknown_model_and_send_actual_value(self):
        config = {'selection_type': 'custom:test', 'model': 'new-model', 'reasoning': {
            'parameter': 'reasoning_effort', 'control': 'effort', 'stages': [
                {'label': 'Fast', 'value': 'low'}, {'label': 'Detailed', 'value': 'custom-high'},
            ],
        }}
        profile = connection_reasoning_profile(config)
        self.assertEqual(profile['options'][1], {'label': 'Detailed', 'value': 'custom-stage:1'})
        body = {}
        apply_cloud_reasoning(body, config, 'new-model', 'custom-stage:1')
        self.assertEqual(body, {'reasoning_effort': 'custom-high'})
        apply_cloud_reasoning(body, config, 'new-model', 'custom-stage:99')
        self.assertEqual(body, {'reasoning_effort': 'low'})

    def test_user_toggle_preserves_boolean_type(self):
        config = {'reasoning': {'parameter': 'enable_thinking', 'control': 'toggle', 'stages': []}}
        for value in (True, False):
            body = {}
            apply_cloud_reasoning(body, config, 'new-model', value)
            self.assertIs(body['enable_thinking'], value)

    def test_custom_connection_requires_enabled_setting_and_parameter(self):
        for settings in (None, {'enabled': False, 'parameter': 'reasoning_effort', 'control': 'toggle'}, {'enabled': True, 'parameter': '', 'control': 'toggle'}):
            config = {'selection_type': 'custom:groq', 'base_url': 'https://api.groq.com/openai/v1', 'model': 'openai/gpt-oss-120b', 'reasoning': settings}
            self.assertEqual(connection_reasoning_profile(config)['control'], 'none')
            body = {}
            apply_cloud_reasoning(body, config, config['model'], True)
            self.assertEqual(body, {})

    def test_groq_cannot_turn_off(self):
        config = cloud_reasoning_profile('custom:test', 'openai/gpt-oss-120b', 'https://api.groq.com/openai/v1')
        self.assertFalse(config['supports_none'])
        self.assertEqual(self.request('custom:test', 'openai/gpt-oss-120b', False, 'https://api.groq.com/openai/v1')['reasoning_effort'], 'low')

    def test_unknown_and_spoofed_hosts_do_not_send_parameters(self):
        for host in ('api.groq.com.evil.test', 'unknown.test'):
            self.assertIsNone(cloud_reasoning_profile('custom:test', 'openai/gpt-oss-120b', f'https://{host}/v1')['adapter'])
        self.assertNotIn('reasoning_effort', self.request('openai', 'gpt-4o', 'high'))

    def test_qwen_effort_and_toggle(self):
        url = 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1'
        self.assertFalse(self.request('custom:test', 'qwen3.8-flash', 'none', url)['enable_thinking'])
        self.assertEqual(self.request('custom:test', 'qwen3.8-flash', 'xhigh', url)['reasoning_effort'], 'xhigh')
        self.assertTrue(self.request('custom:test', 'qwen3.7-flash', True, url)['enable_thinking'])
        self.assertEqual(cloud_reasoning_profile('custom:test', 'qwen3.8-flash', 'https://workspace.ap-southeast-1.maas.aliyuncs.com/v1')['control'], 'effort')

    def test_openai_effort_removes_unsupported_temperature(self):
        body = self.request('openai', 'gpt-5.2', 'none')
        self.assertEqual(body['reasoning_effort'], 'none')
        self.assertNotIn('temperature', body)

    def test_gemini_model_specific_controls(self):
        self.assertEqual(self.request('gemini', 'gemini-3.1-pro-preview', 'medium')['generationConfig']['thinkingConfig'], {'thinkingLevel':'medium'})
        self.assertEqual(self.request('gemini', 'gemini-2.5-flash', False)['generationConfig']['thinkingConfig'], {'thinkingBudget':0})
        self.assertGreater(self.request('gemini', 'gemini-2.5-pro', False)['generationConfig']['thinkingConfig']['thinkingBudget'], 0)

    def test_claude_adaptive_and_manual_budget(self):
        self.assertEqual(self.request('claude', 'claude-sonnet-4-6', 'high')['output_config'], {'effort':'high'})
        body = self.request('claude', 'claude-sonnet-4-5', True)
        self.assertGreaterEqual(body['thinking']['budget_tokens'], 1024)
        self.assertLess(body['thinking']['budget_tokens'], body['max_tokens'])
        self.assertNotIn('temperature', body)
        self.assertFalse(cloud_reasoning_profile('claude', 'claude-opus-5-5')['supports_none'])

if __name__ == '__main__':
    unittest.main()
