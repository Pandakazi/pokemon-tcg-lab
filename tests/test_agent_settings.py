"""Settings transactions use fake transports; no live calls or real API keys."""
import json
import os
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from pokelab import agent_providers as providers
from pokelab.agent_settings import AgentSettings, ApplySettings
from pokelab.agent_research import FLIGHT, ResearchService, ResearchRequest
from pokelab.secrets import SecretStore

KEY = 'fixture-api-key-for-settings'


class MemoryStore:
    def __init__(self):
        self.value = ''
        self.fail = False

    def load(self):
        return self.value

    def save(self, value):
        if self.fail:
            raise OSError('fixture error containing ' + KEY)
        self.value = value


def manager():
    store = MemoryStore()
    settings = AgentSettings(store=store)
    settings.secure = True
    settings.storage = 'encrypted'
    return settings, store


def transport(status=200, text='OK', finish='stop'):
    return httpx.MockTransport(lambda request: httpx.Response(status, json={
        'choices': [{'message': {'content': text}, 'finish_reason': finish}]}))


def apply(settings, provider='openai', **kwargs):
    return list(settings.test_apply(ApplySettings(provider=provider, api_key=KEY), transport=transport(**kwargs)))


@pytest.mark.parametrize('provider', ['openai', 'gemini'])
def test_progress_applies_exactly_one_provider_and_reloads(provider):
    settings, store = manager()
    events = apply(settings, provider)
    assert [event['stage'] for event in events] == ['validating', 'connecting', 'testing', 'saving', 'connected']
    assert events[-1]['settings']['provider'] == provider
    assert events[-1]['settings']['has_key'] is True
    assert KEY not in json.dumps(events) + repr(settings.status())
    restored = AgentSettings(store=store)
    assert restored.configured()[0].provider == provider
    assert restored.key == KEY
    assert providers.PRODUCT_CONNECTION.get() is None


@pytest.mark.parametrize('failure', [dict(status=401), dict(status=403), dict(status=429), dict(status=500),
    dict(text=''), dict(text=KEY), dict(finish='length')])
def test_failed_replace_preserves_active_and_saved_settings(failure):
    settings, store = manager()
    apply(settings)
    saved = store.value
    events = apply(settings, 'gemini', **failure)
    assert events[-1]['stage'] == 'failed'
    assert settings.selection.provider == 'openai' and store.value == saved
    assert KEY not in json.dumps(events)


def test_secure_save_failure_preserves_previous_and_sanitizes_error():
    settings, store = manager()
    apply(settings)
    saved = store.value
    store.fail = True
    events = apply(settings, 'gemini')
    assert events[-1]['stage'] == 'failed'
    assert settings.selection.provider == 'openai' and store.value == saved
    assert KEY not in json.dumps(events)


def test_disconnect_removes_key_and_durably_blocks_environment_fallback(monkeypatch):
    settings, store = manager()
    apply(settings)
    monkeypatch.setenv('POKELAB_RESEARCH_PROVIDER', 'gemini')
    monkeypatch.setenv('POKELAB_RESEARCH_MODEL', 'gemini-3.5-flash-lite')
    assert settings.disconnect()['ok']
    assert KEY not in store.value and not settings.key
    restored = AgentSettings(store=store)
    service = ResearchService({})
    service.settings = restored
    assert service.configured() == (None, 'disconnected')
    assert restored.status()['connected'] is False


def test_corrupt_saved_credential_fails_closed():
    settings, store = manager()
    store.value = 'not JSON'
    restored = AgentSettings(store=store)
    assert restored.managed and restored.configured() == (None, 'secure_storage_unavailable')


def test_unsupported_os_session_only_and_no_plaintext_store():
    settings, store = manager()
    settings.secure, settings.storage = False, 'session'
    assert apply(settings)[-1]['settings']['storage'] == 'session'
    assert store.value == ''
    assert settings.disconnect()['ok'] and store.value == ''


def test_settings_share_single_flight_with_research():
    settings, _ = manager()
    events = settings.test_apply(ApplySettings(provider='openai', api_key=KEY), transport=transport())
    assert next(events)['stage'] == 'validating'
    assert settings.disconnect()['ok'] is False
    assert apply(settings)[-1]['stage'] == 'failed'
    assert ResearchService({}).run(ResearchRequest(scope='conversation', question='Hello'))['status'] == 'busy'
    events.close()
    assert FLIGHT.acquire(blocking=False)
    FLIGHT.release()


def test_product_gate_is_request_local_and_does_not_change_qualification(monkeypatch):
    settings, _ = manager()
    apply(settings)
    monkeypatch.delenv('POKELAB_7B_LIVE_AUTHORIZATION', raising=False)
    assert providers.live_gate(settings.selection) == 'live_not_authorized'
    with settings.activate():
        assert providers.live_gate(settings.selection) is None
        assert providers.secret_present(KEY)
        other = providers.Selection(provider='gemini', model='gemini-3.5-flash-lite')
        assert providers.live_gate(other) == 'live_not_authorized'
    assert providers.PRODUCT_CONNECTION.get() is None


def test_product_transport_sends_only_selected_key_without_mutating_environment(monkeypatch):
    settings, _ = manager()
    apply(settings, 'gemini')
    monkeypatch.setenv('POKELAB_GEMINI_API_KEY', 'legacy-key-must-stay')
    original_client = httpx.Client
    calls = []
    def handle(request):
        calls.append(request)
        assert request.headers['authorization'] == 'Bearer ' + KEY
        assert request.url.host == 'generativelanguage.googleapis.com'
        return httpx.Response(200, json={'choices': [{'message': {'content': 'OK'}, 'finish_reason': 'stop'}], 'usage': {'cost': .001}})
    monkeypatch.setattr(providers.httpx, 'Client', lambda **kwargs: original_client(**dict(kwargs, transport=httpx.MockTransport(handle))))
    with settings.activate():
        result = providers.complete(settings.selection, 'Test', 'Reply OK', max_output=64)
    assert len(calls) == 1 and result.status == 'ok'
    assert result.actual_cost_usd == .001 and result.estimated_cost_usd is None
    assert os.environ['POKELAB_GEMINI_API_KEY'] == 'legacy-key-must-stay'


def test_research_runs_with_secret_quarantine_and_context_is_released(monkeypatch):
    settings, _ = manager()
    apply(settings)
    service = ResearchService({})
    service.settings = settings
    def run(request):
        assert service.configured() == (settings.selection, None)
        assert providers.secret_present(KEY)
        raise RuntimeError(KEY)
    monkeypatch.setattr(service, '_run', run)
    assert service.run(ResearchRequest(scope='conversation', question='Hello')) == dict(status='internal_processing_failure', answer=None)
    assert providers.PRODUCT_CONNECTION.get() is None


@pytest.mark.skipif(os.name != 'nt', reason='Windows DPAPI')
def test_real_dpapi_stores_encrypted_outside_repo_and_disconnect_erases_key(tmp_path):
    settings = AgentSettings(directory=tmp_path)
    assert apply(settings)[-1]['stage'] == 'connected'
    assert KEY.encode() not in settings.store.path.read_bytes()
    restored = AgentSettings(directory=tmp_path)
    assert restored.key == KEY
    assert restored.disconnect()['ok']
    assert KEY not in restored.store.load()
    assert AgentSettings(directory=tmp_path).configured() == (None, 'disconnected')


@pytest.fixture
def client(tmp_path, monkeypatch):
    from pokelab import agent_settings
    from pokelab.api import create_app
    settings, _ = manager()
    monkeypatch.setattr(agent_settings, 'AgentSettings', lambda: settings)
    app = create_app(database=tmp_path/'cards.sqlite3', state_database=tmp_path/'collection.sqlite3',
        competitive_database=tmp_path/'competitive.sqlite3', deck_database=tmp_path/'deck.sqlite3')
    app.state.research_agent.transport = transport()
    with TestClient(app, base_url='http://127.0.0.1') as value:
        yield value, settings


def test_api_progress_and_disconnect_never_return_credentials(client):
    api, settings = client
    result = api.post('/api/v1/settings/agent/test-apply', json=dict(provider='openai', api_key=KEY))
    assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
    events = [json.loads(line) for line in result.text.splitlines()]
    assert events[-1]['stage'] == 'connected' and KEY not in result.text
    assert api.get('/api/v1/settings/agent').json()['provider'] == 'openai'
    result = api.post('/api/v1/settings/agent/disconnect', json={})
    assert result.status_code == 200 and not result.json()['settings']['connected']


@pytest.mark.parametrize('body', [dict(provider='anthropic', api_key=KEY), dict(provider=['openai','gemini'], api_key=KEY),
    dict(provider='gemini', api_key=KEY, model=KEY), dict(provider='gemini', api_key='x'*2049)])
def test_api_validation_is_bounded_and_never_echoes_key(client, body):
    api, _ = client
    result = api.post('/api/v1/settings/agent/test-apply', json=body)
    assert result.status_code == 422 and KEY not in result.text


@pytest.mark.parametrize('endpoint', ['test-apply', 'disconnect'])
def test_api_guards_remote_origin_host_simple_posts_and_oversize(client, endpoint):
    api, _ = client
    url = '/api/v1/settings/agent/' + endpoint
    assert api.post(url, json={}, headers={'origin':'https://evil.example'}).status_code == 403
    assert api.post(url, json={}, headers={'host':'evil.example'}).status_code == 403
    assert api.post(url, json={}, headers={'sec-fetch-site':'cross-site'}).status_code == 403
    assert api.post(url, content='x', headers={'content-type':'text/plain'}).status_code == 415
    assert api.post(url, content='x'*8193, headers={'content-type':'application/json'}).status_code == 413


@pytest.mark.parametrize('key', ['', 'short', 'has spaces in key', 'bad\nkey', 'é'*20])
def test_invalid_key_never_reaches_provider(key):
    settings, _ = manager()
    if not key:
        key = ' '
    query = ApplySettings(provider='openai', api_key=key)
    fake = httpx.MockTransport(lambda _: pytest.fail('Invalid key must not call provider'))
    assert list(settings.test_apply(query, transport=fake))[-1]['stage'] == 'failed'
