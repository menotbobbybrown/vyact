import httpx
import pytest

from services.llm.errors import http_err_msg
from services.llm.messages import MESSAGES
from services.llm.providers import capture_provider_rate_limits


@pytest.mark.parametrize('language', list(MESSAGES))
@pytest.mark.parametrize('status,key', [(401, 'invalid_key'), (429, 'rate_limit'), (503, 'unavailable')])
def test_provider_status_errors_are_localized_even_without_json(language, status, key):
    request = httpx.Request('POST', 'https://example.invalid')
    response = httpx.Response(status, request=request, text='not JSON')
    error = httpx.HTTPStatusError('failed', request=request, response=response)
    assert http_err_msg(error, 'OpenAI', language) == MESSAGES[language][key].format(provider='OpenAI')


@pytest.mark.parametrize('status', [400, 401, 500, 503])
def test_groq_error_preserves_provider_message(status):
    request = httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions')
    response = httpx.Response(status, request=request, json={'error': {'message': 'Exact provider message'}})
    error = httpx.HTTPStatusError('failed', request=request, response=response)
    assert http_err_msg(error, 'OpenAI', 'ko') == 'Exact provider message'


def test_groq_limit_error_uses_localized_notice():
    request = httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions')
    response = httpx.Response(429, request=request, json={'error': {'message': 'Raw rate limit details'}})
    error = httpx.HTTPStatusError('failed', request=request, response=response)
    assert http_err_msg(error, 'OpenAI', 'ko') == MESSAGES['ko']['rate_limit'].format(provider='Groq') + '\n\nHTTP 429\n\nRaw rate limit details'


def test_groq_headers_capture_zero_and_ignore_invalid_values():
    request = httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions')
    usage = {}
    capture_provider_rate_limits(usage, httpx.Response(200, request=request, headers={
        'x-ratelimit-remaining-tokens': '0', 'x-ratelimit-remaining-requests': '998',
    }))
    assert usage == {'provider_rate_limit_is_groq': True, 'provider_remaining_tokens': 0, 'provider_remaining_requests': 998}
    capture_provider_rate_limits(usage, httpx.Response(200, request=request, headers={'x-ratelimit-remaining-tokens': 'bad'}))
    assert usage['provider_remaining_tokens'] == 0


def test_alibaba_headers_use_unspecified_time_window():
    request = httpx.Request('POST', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions')
    usage = {}
    capture_provider_rate_limits(usage, httpx.Response(200, request=request, headers={'x-ratelimit-remaining-tokens': '123', 'x-ratelimit-remaining-requests': '4'}))
    assert usage == {'provider_remaining_tokens': 123, 'provider_remaining_requests': 4}


@pytest.mark.parametrize('status,code', [(429, 'Throttling.RateQuota'), (403, 'AllocationQuota.FreeTierOnly')])
def test_alibaba_quota_errors_are_localized(status, code):
    request = httpx.Request('POST', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions')
    response = httpx.Response(status, request=request, json={'error': {'code': code, 'message': 'Quota exceeded'}})
    error = httpx.HTTPStatusError('failed', request=request, response=response)
    assert http_err_msg(error, 'OpenAI', 'ko') == MESSAGES['ko']['rate_limit'].format(provider='Alibaba Cloud') + f'\n\nHTTP {status} · {code}\n\nQuota exceeded'


def test_groq_limit_includes_code_and_retry_headers():
    request = httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions')
    response = httpx.Response(429, request=request,
        json={'error': {'code': 'rate_limit_exceeded', 'message': 'Limit 8000, requested 9000'}},
        headers={'retry-after': '12', 'x-ratelimit-reset-tokens': '12s', 'x-ratelimit-reset-requests': '1h'})
    error = httpx.HTTPStatusError('failed', request=request, response=response)
    result = http_err_msg(error, 'OpenAI', 'en')
    assert 'HTTP 429 · rate_limit_exceeded' in result
    assert 'Limit 8000, requested 9000' in result
    assert 'retry-after: 12' in result
    assert 'x-ratelimit-reset-tokens: 12s' in result
    assert 'x-ratelimit-reset-requests: 1h' in result


def test_groq_limit_preserves_non_json_body():
    request = httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions')
    response = httpx.Response(429, request=request, text='Raw limit response')
    error = httpx.HTTPStatusError('failed', request=request, response=response)
    assert 'Raw limit response' in http_err_msg(error, 'OpenAI', 'en')
