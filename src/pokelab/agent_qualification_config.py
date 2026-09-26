"""Versioned comparison settings; independent of the frozen message contract."""
from .rules.models import digest

INPUT_BYTES = 32768
RESPONSE_BYTES = 131072
OUTPUT_BYTES = 16384
TIMEOUT_SECONDS = 90
V2_CANDIDATES = (
    ('gemini', 'gemini-3.5-flash-lite'),
    ('openrouter', 'nvidia/nemotron-3-super-120b-a12b:free'),
)


def configuration(version='v1'):
    if version not in ('v1','v2'): raise ValueError('unknown_suite')
    return dict(configuration_schema='pokelab-qualification-config-v1',
        suite='pokelab-qualification-'+version,
        dimension='bounded_synthesis' if version=='v1' else 'quality_qualification',
        max_output_tokens=1200 if version=='v1' else 4096,
        input_bytes=INPUT_BYTES, response_bytes=RESPONSE_BYTES, output_bytes=OUTPUT_BYTES,
        timeout_seconds_per_operation=TIMEOUT_SECONDS, stream=False,
        serial=True, max_selections=8, prior_answers_in_context=False,
        temperature='provider_default', seed='provider_default', reasoning='provider_default',
        output_contract='frozen-ultra-ball-answer-v1', scoring='ultra-ball-grounding-rules-pm-v1',
        partial_output='NOT_EVALUATED', live_policy='explicit-free-only-v1',
        price_ceiling_usd=dict(prompt=0,completion=0,request=0),
        retries=0, fallbacks=False, redirects=False, trust_environment_proxy=False)


def configuration_hash(version='v1'):
    return digest(configuration(version))
