"""Local product settings; one tested provider, atomic encrypted persistence."""
from contextlib import contextmanager
import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from typing import Literal

from . import agent_providers as providers
from .agent_research import FLIGHT
from .secrets import SecretStore

DEFAULT_MODELS = {'openai': 'gpt-4.1-mini', 'gemini': 'gemini-3.5-flash-lite'}


class ApplySettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    provider: Literal['openai', 'gemini']
    api_key: SecretStr = Field(min_length=1, max_length=2048)


class AgentSettings:
    def __init__(self, directory=None, *, store=None):
        # Never derive the secret path from the card DB, user DB or checkout.
        directory = directory or Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'PokeLab' / 'agent-settings'
        self.store = store or SecretStore(Path(directory))
        if store is None:
            self.store.path = Path(directory) / 'web-agent.secret'
        self.secure = os.name == 'nt'
        self.storage = 'encrypted' if self.secure else 'session'
        self.managed = False
        self.selection = None
        self.key = ''
        self.reason = None
        try:
            raw = self.store.load()
            if raw:
                self.managed = True
                record = json.loads(raw)
                if record.get('version') != 1 or type(record.get('enabled')) is not bool:
                    raise ValueError()
                if record['enabled']:
                    self.selection = providers.Selection(provider=record['provider'], model=record['model'])
                    if self.selection.provider not in DEFAULT_MODELS:
                        raise ValueError()
                    self.key = self.valid_key(record['key'])
        except Exception:
            # Corrupt/unreadable credentials never reactivate an env fallback.
            self.managed = True
            self.selection, self.key = None, ''
            self.reason = 'secure_storage_unavailable'

    @staticmethod
    def valid_key(key):
        if not isinstance(key, str):
            raise ValueError()
        key = key.strip()
        if not 8 <= len(key) <= 2048 or not key.isascii() or any(c.isspace() or ord(c) < 33 or ord(c) == 127 for c in key):
            raise ValueError()
        return key

    def configured(self):
        return (self.selection, None) if self.selection and self.key else (None, self.reason or 'disconnected')

    @contextmanager
    def activate(self):
        token = providers.PRODUCT_CONNECTION.set((self.selection, self.key) if self.selection and self.key else None)
        try:
            yield
        finally:
            providers.PRODUCT_CONNECTION.reset(token)

    def status(self, service=None):
        selection, reason = self.configured() if self.managed or service is None else service.configured()
        return dict(provider=selection.provider if selection and selection.provider in DEFAULT_MODELS else None,
            connected=reason is None, has_key=bool(self.key), managed=self.managed,
            storage=self.storage if self.managed else 'external', reason=reason)

    def commit(self, selection, key):
        record = dict(version=1, enabled=selection is not None)
        if selection:
            record.update(provider=selection.provider, model=selection.model, key=key)
        if self.secure:
            self.store.save(json.dumps(record, separators=(',', ':')))
        # Unsupported OS: session only, no plaintext fallback or key in browser.
        self.managed, self.selection, self.key, self.reason = True, selection, key, None

    def test_apply(self, query, *, transport=None):
        if not FLIGHT.acquire(blocking=False):
            yield dict(stage='failed', message='The Agent is busy. Wait for the current request, then try again.')
            return
        try:
            yield dict(stage='validating', message='Validating API key…')
            try:
                key = self.valid_key(query.api_key.get_secret_value())
                model = (os.getenv('POKELAB_RESEARCH_MODEL') if os.getenv('POKELAB_RESEARCH_PROVIDER') == query.provider else None)
                model = model or os.getenv('POKELAB_' + query.provider.upper() + '_MODEL') or DEFAULT_MODELS[query.provider]
                selection = providers.Selection(provider=query.provider, model=model)
            except (ValueError, TypeError):
                yield dict(stage='failed', message='Enter a valid API key and check the configured model.')
                return
            label = 'OpenAI' if query.provider == 'openai' else 'Gemini'
            yield dict(stage='connecting', message='Connecting to ' + label + '…')
            token = providers.PRODUCT_CONNECTION.set((selection, key))
            try:
                result = providers.complete(selection, 'This is a connection test. Reply with OK only.',
                    'Reply OK.', transport=transport, max_output=64)
            finally:
                providers.PRODUCT_CONNECTION.reset(token)
            yield dict(stage='testing', message='Checking Agent response…')
            if result.status != 'ok' or result.finish_reason not in ('stop', 'end_turn') or not result.text.strip():
                messages = {'http_401': 'The API key was rejected. Check it and try again.',
                    'http_403': 'The provider denied access. Check your key and model access.',
                    'http_429': 'The provider is rate limited or out of quota. Try again later.'}
                yield dict(stage='failed', message=messages.get(result.status, 'Couldn’t connect to ' + label + '. Check your key, model access and connection.'))
                return
            yield dict(stage='saving', message='Saving securely…' if self.secure else 'Applying for this session…')
            try:
                self.commit(selection, key)
            except Exception:
                yield dict(stage='failed', message='Secure storage is unavailable. The previous settings are unchanged.')
                return
            yield dict(stage='connected', message=label + ' connected.', settings=self.status())
        except Exception:
            yield dict(stage='failed', message='Unable to apply Agent settings. The previous settings are unchanged.')
        finally:
            FLIGHT.release()

    def disconnect(self):
        if not FLIGHT.acquire(blocking=False):
            return dict(ok=False, message='The Agent is busy. Wait for the current request, then disconnect.')
        try:
            # An encrypted disabled record removes the key and prevents env
            # configuration from silently reconnecting after a restart.
            self.commit(None, '')
            return dict(ok=True, settings=self.status())
        except Exception:
            return dict(ok=False, message='Unable to remove the saved credential. The previous settings are unchanged.')
        finally:
            FLIGHT.release()
