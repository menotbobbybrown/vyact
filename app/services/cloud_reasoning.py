"""Cloud model reasoning capabilities and matching request parameters."""
import re
from urllib.parse import urlparse

EFFORTS = ['low', 'medium', 'high']

def cloud_reasoning_profile(provider: str, model: str, base_url: str = '') -> dict:
    model = (model or '').lower()
    host = (urlparse(base_url or '').hostname or '').lower()
    if provider.startswith('custom:'):
        provider = 'groq' if host == 'api.groq.com' else 'alibaba' if host == 'dashscope.aliyuncs.com' or host == 'dashscope-intl.aliyuncs.com' or host.endswith('.maas.aliyuncs.com') else 'openai' if host == 'api.openai.com' else 'unknown'
    profile = {'control': 'none', 'efforts': [], 'supports_none': False, 'adapter': None}
    def effort(adapter, values=EFFORTS, off=False):
        return {'control': 'effort', 'efforts': list(values), 'supports_none': off, 'adapter': adapter}
    if provider == 'groq' and model in {'openai/gpt-oss-120b', 'openai/gpt-oss-20b'}:
        return effort('openai_effort')
    if provider == 'alibaba':
        if model.startswith(('qwen3.8-flash', 'qwen3.8-max')):
            return effort('qwen_effort', ['low', 'medium', 'xhigh'], True)
        if model.startswith(('qwen3.7-flash', 'qwen3.7-plus', 'qwen3.6-flash', 'qwen3.5-flash', 'qwen3.5-plus')):
            return {'control': 'toggle', 'efforts': [], 'supports_none': True, 'adapter': 'qwen_toggle'}
    if provider == 'openai':
        if model.startswith(('gpt-5.2', 'gpt-5.3', 'gpt-5.4')) and 'pro' not in model:
            return effort('openai_effort', EFFORTS + ['xhigh'], True)
        if model.startswith('gpt-5.1'):
            return effort('openai_effort', off=True)
        if model.startswith(('o1', 'o3', 'o4', 'gpt-5')) and not any(x in model for x in ('pro', 'chat', 'o1-mini', 'o1-preview')):
            return effort('openai_effort')
    if provider == 'gemini':
        if re.match(r'gemini-3(?:[.-])', model) and 'image' not in model:
            values = ['low', 'high'] if model.startswith('gemini-3-pro') else EFFORTS
            if 'flash' in model and not model.startswith(('gemini-3.7-', 'gemini-3.8-')):
                values = ['minimal'] + list(values)
            return effort('gemini_level', values)
        if model.startswith('gemini-2.5-') and 'image' not in model and 'audio' not in model:
            return effort('gemini_budget', off='flash' in model)
    if provider == 'claude':
        if re.match(r'claude-(opus-4-[678]|sonnet-4-6|opus-5|sonnet-5)', model):
            values = EFFORTS + (['xhigh', 'max'] if model.startswith(('claude-opus-4-7', 'claude-opus-4-8', 'claude-opus-5', 'claude-sonnet-5')) else ['max'] if model.startswith('claude-opus-4-6') else [])
            return effort('claude_adaptive', values, off=not model.startswith(('claude-opus-5-5', 'claude-sonnet-5-5')))
        if re.match(r'claude-(sonnet-4|opus-4|haiku-4-5|3-7-sonnet)', model):
            return {'control': 'toggle', 'efforts': [], 'supports_none': True, 'adapter': 'claude_budget'}
    return profile

def connection_reasoning_profile(config: dict) -> dict:
    settings = config.get('reasoning')
    if settings and (not settings.get('enabled', True) or not settings.get('parameter', '').strip()):
        return {'control': 'none', 'efforts': [], 'supports_none': False, 'adapter': None}
    if not settings and config.get('selection_type', '').startswith('custom:'):
        return {'control': 'none', 'efforts': [], 'supports_none': False, 'adapter': None}
    if settings:
        options = [{'label': stage['label'], 'value': f'custom-stage:{index}'} for index, stage in enumerate(settings.get('stages', []))]
        return {'control': settings['control'], 'efforts': [option['value'] for option in options], 'options': options, 'supports_none': False, 'adapter': 'custom'}
    return cloud_reasoning_profile(config.get('selection_type', config.get('type', '')), config.get('model', ''), config.get('base_url') or '')

def apply_cloud_reasoning(body: dict, config: dict, model: str, value: bool | str | None) -> None:
    settings = config.get('reasoning')
    if settings and (not settings.get('enabled', True) or not settings.get('parameter', '').strip()):
        return
    if not settings and config.get('selection_type', '').startswith('custom:'):
        return
    if settings:
        if settings['control'] == 'toggle':
            body[settings['parameter']] = value is True or value == 'on'
        else:
            stages = settings.get('stages', [])
            selected = next((stage for index, stage in enumerate(stages) if value == f'custom-stage:{index}'), stages[0] if stages else None)
            if selected:
                body[settings['parameter']] = selected['value']
        return
    profile = cloud_reasoning_profile(config.get('selection_type', config.get('type', '')), model, config.get('base_url') or '')
    adapter = profile['adapter']
    if not adapter or value is None:
        return
    off = value is False or value in ('none', 'off')
    effort = value if isinstance(value, str) and value in profile['efforts'] else profile['efforts'][0] if profile['efforts'] else 'low'
    off = off and profile['supports_none']
    if adapter == 'openai_effort':
        body['reasoning_effort'] = 'none' if off else effort
        body.pop('temperature', None)
    elif adapter in ('qwen_effort', 'qwen_toggle'):
        body['enable_thinking'] = not off
        if not off and adapter == 'qwen_effort':
            body['reasoning_effort'] = effort
    elif adapter in ('gemini_level', 'gemini_budget'):
        body['generationConfig']['thinkingConfig'] = {'thinkingLevel': effort} if adapter == 'gemini_level' else {'thinkingBudget': 0 if off else {'low': 1024, 'medium': 4096, 'high': 8192}[effort]}
    elif adapter.startswith('claude_'):
        body.pop('temperature', None)
        if off:
            body['thinking'] = {'type': 'disabled'}
            if adapter == 'claude_adaptive':
                body['output_config'] = {'effort': 'low'}
        elif adapter == 'claude_adaptive':
            body['thinking'] = {'type': 'adaptive'}
            body['output_config'] = {'effort': effort}
        else:
            # Manual thinking needs at least 1024 tokens and room for the answer.
            body['max_tokens'] = max(body['max_tokens'], 2048)
            body['thinking'] = {'type': 'enabled', 'budget_tokens': min(1024, body['max_tokens'] - 1)}
