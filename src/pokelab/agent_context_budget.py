"""Local context projection only; saved artifacts and retrieval order never change."""
from copy import deepcopy
from .agent_research import canonical, ResearchUnavailable


class RequiredContextOverflow(ResearchUnavailable):
    def __init__(self, diagnostics):
        super().__init__('budget_exceeded')
        self.diagnostics = diagnostics


def size(value):
    return len(canonical(value).encode())


def fit(envelope, limit):
    """Shed support, never task/identity/counts/constraints/pending proposals.

    All candidate identities remain available in the original retrieval order.
    The final floor removes optional printed/support data, not candidate access.
    Resolution/legality still reads the local database, not this projection.
    """
    e = deepcopy(envelope)
    before = size(e)
    e.pop('content_hash', None)
    e.pop('context_budget', None)
    steps = []
    # Include actual bounded accounting/hash overhead; do not refuse merely to
    # leave arbitrary headroom when the required packet still fits.
    def bounded():
        return dict(e, content_hash='0'*64, context_budget=dict(budget_bytes=limit,
            before_bytes=before, compacted_bytes=size(e), trims=steps))
    def over(): return size(bounded()) > limit
    def note(code):
        if code not in steps: steps.append(code)
    if over():
        # Tier 4: presentation provenance and repeated evidence IDs.
        seen = set(); evidence = []
        for item in e['evidence']:
            if item['id'] in seen: continue
            seen.add(item['id'])
            evidence.append({k:v for k,v in item.items() if k not in ('url','checked_at','references')})
        e['evidence'] = evidence
        note('deduplicate_provenance')
        if e.get('current_generated_deck'):
            e['artifacts'].pop('generated_deck', None)
            # The current exact artifact and pending proposal are explicit below;
            # this old raw proposal is a duplicate, not pending change authority.
            e['previous_proposal'] = None
            note('duplicate_generated_artifact')
    if over() and e.get('generated_intent'):
        # Tier 3: repeated baseline/card annotations; retain baseline quantities.
        sandbox = e.get('candidate_sandbox', {})
        c = sandbox.get('consensus')
        if c:
            sandbox['consensus'] = {k:v for k,v in c.items() if k in (
                'status','label','source','event_ids','sample_size','placement_band',
                'placement_weights','shape','energy','cards')}
            sandbox['consensus']['cards'] = [{k:r[k] for k in ('candidate_id','quantity') if k in r} for r in c.get('cards',[])]
        fields = ('candidate_id','printing_id','name','category','role','ace_spec',
            'basic_energy','copy_limit_name','requested_core','predecessor_candidate_ids',
            'stage','evolveFrom','types','attacks','abilities','effect','rules','hp',
            'trainerType','energyType')
        sandbox['candidates'] = [{k:r[k] for k in fields if k in r} for r in sandbox.get('candidates',[])]
        sandbox.pop('instruction', None)  # same constraints in the system contract
        note('compact_candidate_support')
    if over():
        # Tier 3: selected card and active snapshot stay; other printed data is
        # already available through candidates/local fact review/on-demand proof.
        selected = (e.get('selected') or {}).get('printing')
        e['evidence'] = [r for r in e['evidence'] if not r.get('printing') or r['printing']==selected]
        note('optional_card_evidence')
    while over() and e['history']:
        e['history'] = e['history'][1:]
        note('older_conversation')
    if over() and e.get('generated_intent'):
        # Keep every ID/name/construction flag. Omitted text is unknown, never
        # permission to invent mechanics; deterministic validation is unchanged.
        for r in e.get('candidate_sandbox',{}).get('candidates',[]):
            for k in ('attacks','abilities','effect','rules','hp'):r.pop(k,None)
        note('optional_printed_text')
    if over():
        # Tier 2 is optional before refusing Tier 1. No complete proof graph is
        # mandatory for strategic judgment. Active/selected facts stay authority.
        e['evidence'] = [r for r in e['evidence'] if r['id']=='active-deck' or
            r.get('printing') and r['printing']==(e.get('selected') or {}).get('printing')]
        if e.get('generated_intent'):
            for k in ('consensus','competitive_prior','limitations'):
                e.get('candidate_sandbox',{}).pop(k,None)
        note('optional_competitive_support')
    if over():
        # Other historical artifacts are optional when a current deck is explicit;
        # pending proposal state is kept separately, including source ID/hash.
        if e.get('current_generated_deck'):e['artifacts'] = {}
        note('other_historical_artifacts')
    if over():
        raise RequiredContextOverflow(dict(condition='required_context_overflow',
            budget_bytes=limit, required_bytes=size(bounded()), provider_called=False))
    e['context_budget'] = dict(budget_bytes=limit, before_bytes=before,
        compacted_bytes=size(e), trims=steps)
    return e
