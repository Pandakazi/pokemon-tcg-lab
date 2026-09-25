"""Stable, source-qualified research URLs; labels and list URLs are not identity."""
import hashlib


def archetype_key(source_id):
    return hashlib.sha256(('limitless-main:archetype:'+source_id).encode()).hexdigest()[:24]


def evidence_key(event_id, rank):
    return hashlib.sha256(f'limitless-main:result:{event_id}:{rank}'.encode()).hexdigest()[:24]
