"""Bounded text transport, no tools, routing, retries, logging or credential storage."""
import base64
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from urllib.parse import quote
import httpx

from .agent_context_models import Frozen
from pydantic import Field
from typing import Literal


@dataclass(frozen=True)
class Provider:
    endpoint: str
    variable: str | None
    anthropic: bool = False


PROVIDERS = {
    'openai': Provider('https://api.openai.com/v1/chat/completions','POKELAB_OPENAI_API_KEY'),
    'gemini': Provider('https://generativelanguage.googleapis.com/v1beta/openai/chat/completions','POKELAB_GEMINI_API_KEY'),
    'anthropic': Provider('https://api.anthropic.com/v1/messages','POKELAB_ANTHROPIC_API_KEY',True),
    'xai': Provider('https://api.x.ai/v1/chat/completions','POKELAB_XAI_API_KEY'),
    'mistral': Provider('https://api.mistral.ai/v1/chat/completions','POKELAB_MISTRAL_API_KEY'),
    'deepseek': Provider('https://api.deepseek.com/chat/completions','POKELAB_DEEPSEEK_API_KEY'),
    'openrouter': Provider('https://openrouter.ai/api/v1/chat/completions','POKELAB_OPENROUTER_API_KEY'),
    'ollama': Provider('http://127.0.0.1:11434/v1/chat/completions',None),
}


class Selection(Frozen):
    provider: Literal['openai','gemini','anthropic','xai','mistral','deepseek','openrouter','ollama']
    model: str = Field(min_length=1,max_length=160,pattern=r'^[A-Za-z0-9_.:/-]+$')


class Response(Frozen):
    status: str
    text: str = ''
    latency_ms: int
    reported_model: str | None = None
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    estimated_cost_usd: float | None = None
    actual_cost_usd: float | None = None
    cost_basis: str = 'unreported'


def secret_forms():
    """Only explicitly named credential variables; never enumerate/dump environment."""
    values=[os.environ.get(p.variable,'') for p in PROVIDERS.values() if p.variable]
    forms=set()
    for value in filter(None,values):
        forms.update((value,quote(value,safe=''),json.dumps(value)[1:-1],
                      base64.b64encode(value.encode()).decode(),base64.urlsafe_b64encode(value.encode()).decode()))
    return tuple(forms)


def secret_present(text):
    return any(value in text for value in secret_forms())


def live_gate(selection):
    if os.environ.get('POKELAB_7B_LIVE_AUTHORIZATION') != 'PM_APPROVED_ZERO_COST':
        return 'live_not_authorized'
    if selection.provider=='gemini':
        # 2.5 access is restricted to prior users. Pin the documented new-project
        # free-tier replacement; never silently substitute a requested model.
        if selection.model != 'gemini-3.5-flash-lite': return 'model_not_free_qualified'
        if os.environ.get('POKELAB_GEMINI_FREE_TIER_CONFIRMED')!='NO_BILLING': return 'free_tier_not_confirmed'
    elif selection.provider=='openrouter':
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+:free',selection.model): return 'explicit_free_model_required'
    elif selection.provider=='ollama':
        if '/' in selection.model or 'cloud' in selection.model.lower(): return 'local_model_required'
        if os.environ.get('POKELAB_OLLAMA_LOCAL_CONFIRMED')!='LOCAL_ONLY': return 'local_model_not_confirmed'
    else: return 'paid_provider_disabled'
    return None


def complete(selection, system, user, *, transport=None, max_output=1200):
    """Mocks must be httpx.MockTransport. All real sockets require the live gate."""
    selection=Selection.model_validate(selection.model_dump())
    fake=isinstance(transport,httpx.MockTransport)
    started=time.monotonic()
    def failed(status): return Response(status=status,latency_ms=round((time.monotonic()-started)*1000))
    if transport is not None and not fake: return failed('unsupported_transport')
    if secret_present(system+user+selection.model): return failed('secret_input_rejected')
    if len((system+user).encode())>32768 or not 1<=max_output<=1600: return failed('request_budget_exceeded')
    if not fake:
        blocked=live_gate(selection)
        if blocked: return failed(blocked)
    provider=PROVIDERS[selection.provider]
    credential=os.environ.get(provider.variable,'') if provider.variable and not fake else ''
    if provider.variable and not credential and not fake: return failed('missing_credential')
    headers={'content-type':'application/json'}
    # Fake requests never carry actual environment credentials.
    if credential:
        headers['x-api-key' if provider.anthropic else 'authorization']=credential if provider.anthropic else 'Bearer '+credential
    messages=[{'role':'system','content':system},{'role':'user','content':user}]
    payload={'model':selection.model,'messages':messages,'stream':False}
    if provider.anthropic:
        headers['anthropic-version']='2023-06-01'
        payload.update(system=system,messages=messages[1:],max_tokens=max_output)
    else:
        payload['max_completion_tokens' if selection.provider=='openai' else 'max_tokens']=max_output
    if selection.provider=='openrouter':
        payload['provider']={'allow_fallbacks':False,'max_price':{'prompt':0,'completion':0,'request':0}}
    # Prevent HTTP debug logging from emitting headers/body. No raw response/request is returned.
    previous=logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with httpx.Client(transport=transport,timeout=90,follow_redirects=False,trust_env=False) as client:
            with client.stream('POST',provider.endpoint,json=payload,headers=headers) as response:
                if response.status_code!=200: return failed('http_'+str(response.status_code))
                chunks=[]; length=0
                for chunk in response.iter_bytes():
                    length+=len(chunk)
                    if length>131072: return failed('response_too_large')
                    chunks.append(chunk)
                raw=b''.join(chunks).decode('utf-8')
        if secret_present(raw): return failed('secret_response_quarantined')
        data=json.loads(raw)
        if secret_present(json.dumps(data,ensure_ascii=False)): return failed('secret_response_quarantined')
        if provider.anthropic:
            if any(c.get('type')=='tool_use' for c in data.get('content',[])): return failed('tool_output_rejected')
            text='\n'.join(c['text'] for c in data['content'] if c.get('type')=='text')
            finish=data.get('stop_reason')
        else:
            choice=data['choices'][0]; message=choice['message']
            if message.get('tool_calls') or message.get('function_call'): return failed('tool_output_rejected')
            text=message.get('content'); finish=choice.get('finish_reason')
        if finish not in (None,'stop','end_turn'): return failed('incomplete_or_blocked_output')
        if not isinstance(text,str) or not text.strip(): return failed('empty_output')
        if len(text.encode())>16384: return failed('output_too_large')
        usage=data.get('usage') or {}
        def count(key):
            value=usage.get(key)
            return value if type(value) is int and value>=0 else None
        reasoning=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens')
        reasoning=reasoning if type(reasoning) is int and reasoning>=0 else None
        cost=usage.get('cost')
        cost=cost if type(cost) in (int,float) and 0<=cost<1000000 else None
        reported=data.get('model')
        reported=reported if isinstance(reported,str) and len(reported)<=160 else None
        return Response(status='nonzero_cost_reported_stop' if not fake and cost and cost>0 else 'ok',text=text,latency_ms=round((time.monotonic()-started)*1000),
            reported_model=reported,finish_reason=finish if isinstance(finish,str) else None,
            input_tokens=count('input_tokens' if provider.anthropic else 'prompt_tokens'),
            output_tokens=count('output_tokens' if provider.anthropic else 'completion_tokens'),reasoning_tokens=reasoning,
            estimated_cost_usd=0 if not fake else None,actual_cost_usd=cost,
            cost_basis='mock-no-charge' if fake else 'provider-reported' if cost is not None else 'zero-cost-policy; actual billing unreported')
    except Exception:
        # Never propagate provider bodies, request/header objects or exception text.
        return failed('transport_or_response_error')
    finally:
        logging.disable(previous)
