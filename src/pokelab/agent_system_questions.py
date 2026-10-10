"""Narrow local product explanations. No retrieval, provider execution or actions."""
import re


def respond(service,request,history):
    q=request.question.casefold().replace('’',"'").strip(' \t\r\n?.!')
    text=None
    if re.fullmatch(r'(?:what is|what\'s|explain) (?:the )?evidence budget',q):
        from .agent_conversation import CONTEXT_BYTES
        from .agent_qualification_config import INPUT_BYTES
        text=('The evidence budget bounds the supporting context sent with a provider request. '
            f'PokéLab allows up to {CONTEXT_BYTES:,} bytes of conversational context within a {INPUT_BYTES:,}-byte total input limit. '
            'It preserves your question, authoritative deck, artifact identity, pending changes and construction constraints, '
            'then deduplicates and trims lower-priority evidence. It refuses before calling the model only when required context cannot fit. '
            'This input limit is separate from the model’s output-token allowance.')
    elif re.fullmatch(r'(?:why did (?:that fail|pok[eé]lab refuse (?:that|this))|why was (?:that|this) refused)',q):
        incident=history.get('last_incident')
        if incident and incident.get('kind')=='context_budget':
            text='The previous request exceeded the context budget before the model was called. After trimming optional support, the required task and state still could not fit. Your deck and pending changes were preserved.'
        else:text='No structured failure incident is available in this conversation, so I cannot establish why that request was refused.'
    elif re.fullmatch(r'(?:how does|explain) (?:the )?(?:recent )?consensus baseline(?: work)?',q):
        text=('The baseline uses cached recent Limitless lists for the matching archetype/variant. '
            'It starts with recent events, expands placement depth before reaching farther back, and requires at least eight usable lists. '
            'Modest placement weights produce average copies and deck shape; deterministic construction resolves a legal 60-card baseline. '
            'It is empirical composition evidence, not proof of pilot intent or guaranteed performance.')
    elif re.fullmatch(r'(?:what does|what is|explain) (?:validated|validation)(?: mean)?',q):
        text='Validated means the resolved artifact passed PokéLab’s current identity, Standard legality, quantity and construction checks. It does not establish strategic strength, tournament performance or a reviewed ruling, and it does not save or apply the deck.'
    elif re.fullmatch(r'why (?:does it say |is (?:it|this) )?proposal only',q):
        text='The exact cuts and additions are retained as a proposal tied to the current generated deck. They do not change that deck until you explicitly ask to apply them here. This does not save or modify Deck Builder or collection ownership.'
    elif re.fullmatch(r'what data are you using',q):
        text='PokéLab uses local card data, the supplied deck or conversation artifact, and available cached competitive evidence. Collection and reviewed-rules evidence are included only where available and relevant. It is not browsing the web; model strategy is interpretation rather than new factual authority. Ask to show sources for the research evidence snapshot.'
    elif re.fullmatch(r'(?:how does|explain) (?:the )?(?:candidate )?sandbox(?: work)?',q):
        text='The candidate sandbox is a bounded set of locally resolved Standard-legal functional card identities. The model selects supplied candidate IDs; PokéLab then validates identities, quantities and construction against local data. It is not unrestricted card invention and does not write to your decks or collection.'
    if text is None:return None
    from .agent_generation import finish
    envelope=dict(version='pokelab-conversation-v1',policy='conversational_default',
        question=request.question,lifecycle='EXPLORE',route='system',artifact_mutation_allowed=False,
        evidence=[],omissions=[],proof_requested=False,external_research=False,
        selected=None,revision=request.revision if request.include_deck else None,window=request.window)
    answer=dict(version='pokelab-conversation-answer-v1',paragraphs=[dict(text=text,evidence=[])],facts=[],notices=[])
    result=finish(service,request,history,envelope,answer,history.get('artifacts',{}))
    result.setdefault('execution',{})['mode']='local_system'
    return result
