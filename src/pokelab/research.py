"""Read-only research over the existing main-Limitless store. No ingestion or AI."""
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from statistics import median

from tcg_lab.cards import summary
from tcg_lab.models import Deck, DeckEntry
from tcg_lab.service import Lab
from .collection import representative_printings
from .competitive import ARCHETYPE_PREVALENCE_MIN_DECKS
from .decks import DeckProvider, deck_identity
from .limitless_main import SOURCE
from .images import TCGdexImages
from .research_identity import archetype_key, evidence_key


class Research:
    def __init__(self, competitive, collection):
        self.competitive, self.collection = competitive, collection

    def archetype(self, key):
        if not self.competitive.path.exists():
            raise KeyError('Archetype is not present in the local evidence.')
        with closing(self.competitive.connect()) as db:
            rows = db.execute("SELECT DISTINCT json_extract(raw,'$.archetype_id') id,json_extract(raw,'$.archetype_name') name FROM competitive_decks WHERE source=? ORDER BY id,name", (SOURCE,))
            for row in rows:
                if archetype_key(row['id']) == key:
                    return dict(row)
        raise KeyError('Archetype is not present in the local evidence.')

    def selected(self, key, window='30', today=None):
        archetype = self.archetype(key)
        today = today or datetime.now(timezone.utc).date()
        if window not in ('7','30','90','format'):
            raise ValueError('Unsupported timeframe')
        configured = self.competitive.format_start
        available = configured is not None and configured <= today
        start = configured if window == 'format' else today-timedelta(days=int(window)-1)
        with closing(self.competitive.connect()) as db:
            events = [dict(r) for r in db.execute('SELECT * FROM competitive_events WHERE source=? AND date>=? AND date<=? ORDER BY date,id', (SOURCE, start.isoformat() if start else '9999-12-31', today.isoformat()))]
            rows = db.execute('''SELECT d.* FROM competitive_decks d JOIN competitive_events e
                ON e.source=d.source AND e.id=d.event_id WHERE d.source=? AND e.date>=? AND e.date<=?
                AND json_extract(d.raw,'$.archetype_id')=? ORDER BY e.date DESC,d.event_id,d.rank''',
                (SOURCE,start.isoformat() if start else '9999-12-31',today.isoformat(),archetype['id']))
            decks = [{**dict(r),'raw':json.loads(r['raw']),'cards':json.loads(r['cards'])} for r in rows]
            status = db.execute('SELECT error FROM competitive_status WHERE source=?',(SOURCE,)).fetchone()
        eligible = [d for d in decks if d['resolved']]
        represented = {d['event_id'] for d in decks}
        provenance = [{**json.loads(e['raw']),'fetched_at':e['fetched_at']} for e in events if e['id'] in represented]
        n = len(eligible)
        header = dict(id=key,source_id=archetype['id'],name=archetype['name'],source=SOURCE,window=window,
            format_available=available,format_start=configured.isoformat() if configured else None,
            period_start=start.isoformat() if start else None,period_end=today.isoformat(),
            evidence_start=min((e['date'] for e in provenance),default=None),evidence_end=max((e['date'] for e in provenance),default=None),
            status='format_unavailable' if window=='format' and not available else 'observed' if n>=ARCHETYPE_PREVALENCE_MIN_DECKS else 'limited_evidence' if n else 'mapping_failure' if decks else 'no_data',
            eligible_decks=n,published_decks=len(decks),excluded_unmapped=len(decks)-n,tournament_count=len(provenance),
            results_without_lists=sum(e['results']-e['published'] for e in events),
            results_without_lists_scope='All cached tournaments in this timeframe; archetype of results without lists is not stored.',
            prevalence_min_decks=ARCHETYPE_PREVALENCE_MIN_DECKS,source_error=status['error'] if status else None,provenance=provenance)
        return header, decks, {e['id']:e for e in events}

    def references(self, ids):
        catalog = self.collection.catalog()
        snapshot = self.collection.snapshot()
        refs = representative_printings(self.competitive.cards,ids,catalog)
        output = {}
        for fid in ids:
            ref = refs.get(fid)
            # Historical mappings with no current Standard representative remain inspectable.
            if not ref and fid in catalog[1]:
                printing = sorted(catalog[1][fid])[0]
                ref = dict(printing_id=printing,image_url=TCGdexImages().url(catalog[0][printing]['card'],large=True))
            card = None
            if ref:
                record = catalog[0][ref['printing_id']]
                card = {**summary(record['card'],False),'image_url':ref['image_url'],
                    'deck_identity':deck_identity(record),
                    'legality_provenance':dict(source='TCGdex',checked_at=record['checked_at'])}
            output[fid] = dict(functional_id=fid,card=card,owned=snapshot.functional_totals.get(fid,0))
        return output

    @staticmethod
    def distributions(decks):
        ids = sorted({fid for d in decks for fid in d['cards']})
        return {fid:Counter(d['cards'].get(fid,0) for d in decks) for fid in ids}

    def statistics(self, key, window='30', today=None):
        header, rows, _ = self.selected(key,window,today)
        decks = [d for d in rows if d['resolved']]
        n = len(decks); distributions = self.distributions(decks)
        refs = self.references(distributions) if distributions else {}
        cards = []
        for fid, buckets in distributions.items():
            included = n-buckets[0]; total = sum(q*count for q,count in buckets.items())
            cards.append(dict(**refs[fid],included_decks=included,eligible_decks=n,
                inclusion_percent=100*included/n if n>=ARCHETYPE_PREVALENCE_MIN_DECKS and header['source_id']!='unknown' else None,
                total_copies=total,average_when_included=total/included,average_all_decks=total/n,
                median_copies=median([q for q,count in buckets.items() for _ in range(count)]),
                distribution=[dict(quantity=q,decks=count) for q,count in sorted(buckets.items())]))
        cards.sort(key=lambda c:(-c['included_decks'],-c['total_copies'],c['functional_id']))
        return dict(archetype_id=key,window=window,cards=cards)

    @staticmethod
    def observation(deck, event):
        raw, metadata = deck['raw'], json.loads(event['raw'])
        return dict(id=evidence_key(deck['event_id'],deck['rank']),event_id=deck['event_id'],
            event=metadata['name'],date=event['date'],player=raw['player'],placement=deck['rank'],
            archetype_id=archetype_key(raw['archetype_id']),archetype_source_id=raw['archetype_id'],archetype=raw['archetype_name'],
            source_url=raw.get('list_url'),event_url=metadata['url'],mapped=bool(deck['resolved']),fetched_at=event['fetched_at'])

    def evidence_page(self,key,window='30',page=1,page_size=20,include_excluded=False,today=None):
        _, decks, events = self.selected(key,window,today)
        selected = [d for d in decks if include_excluded or d['resolved']]
        return dict(archetype_id=key,window=window,total=len(selected),page=page,page_size=page_size,
            next_page=page+1 if page*page_size<len(selected) else None,
            decks=[self.observation(d,events[d['event_id']]) for d in selected[(page-1)*page_size:page*page_size]])

    def deck_cards(self, counts):
        refs = self.references(counts)
        cards = [dict(**refs[fid],quantity=q) for fid,q in sorted(counts.items())]
        categories = Counter()
        for row in cards:
            categories[row['card']['category'] if row['card'] else 'Unknown'] += row['quantity']
        return cards, dict(categories)

    def tournament_deck(self, key):
        if not self.competitive.path.exists():
            raise KeyError('Tournament evidence not found.')
        with closing(self.competitive.connect()) as db:
            # Scan only compact identity columns, then fetch one observation and its provenance.
            found = next((r for r in db.execute('SELECT event_id,rank FROM competitive_decks WHERE source=?',(SOURCE,)) if evidence_key(r['event_id'],r['rank'])==key),None)
            if not found:
                raise KeyError('Tournament evidence not found.')
            deck = dict(db.execute('SELECT * FROM competitive_decks WHERE source=? AND event_id=? AND rank=?',(SOURCE,found['event_id'],found['rank'])).fetchone())
            event = dict(db.execute('SELECT * FROM competitive_events WHERE source=? AND id=?',(SOURCE,found['event_id'])).fetchone())
            pages = [dict(r) for r in db.execute('SELECT url,sha256,parser FROM competitive_pages WHERE source=? AND event_id=? ORDER BY url',(SOURCE,found['event_id']))]
        deck['raw'], deck['cards'] = json.loads(deck['raw']), json.loads(deck['cards'])
        cards, categories = self.deck_cards(deck['cards'])
        return dict(source=SOURCE,observation=self.observation(deck,event),cards=cards,categories=categories,
            card_count=sum(c['count'] for c in deck['raw']['cards']),mapped_card_count=sum(deck['cards'].values()),
            published_cards=deck['raw']['cards'],unmapped_cards=deck['raw'].get('unmapped_cards',[]),pages=pages,
            presentation_note='Observed tournament deck. Artwork represents functional cards; source exact finish is not established. Original published set/number lines are preserved below.')

    def composite(self,key,window='30',today=None):
        header, rows, _ = self.selected(key,window,today)
        decks = [d for d in rows if d['resolved']]
        result = dict(archetype_id=key,window=window,label='Archetype Composite',algorithm='validated-observed-medoid-v1',
            status='unavailable',sample_size=len(decks),limited_evidence=len(decks)<ARCHETYPE_PREVALENCE_MIN_DECKS,
            total=0,categories={},cards=[],reasons=[],limitations=['Analytical synthesis, not an actual tournament result or a claim of optimality.',
                'Candidate quantities are constrained to observed whole-deck vectors; unavailable does not prove no other valid synthesis exists.',
                'Uses current source Standard flags and inherited supported checks, not exhaustive tournament legality or historical rulings.'])
        if not decks:
            result['reasons']=['Format start not configured or unavailable.' if header['status']=='format_unavailable' else 'No mapped decks in this timeframe.']
            return result
        distributions = self.distributions(decks)
        vectors = {tuple(sorted(d['cards'].items())) for d in decks}
        # Minimize absolute copy-count distance to every entrant, then prefer more
        # commonly included cards. Exact sorted functional ID/count vector breaks ties.
        def score(vector):
            counts = dict(vector)
            distance = sum(freq*abs(counts.get(fid,0)-q) for fid,buckets in distributions.items() for q,freq in buckets.items())
            inclusion = sum(len(decks)-distributions[fid][0] for fid,_ in vector)
            return distance,-inclusion,vector
        catalog = self.collection.catalog()
        provider = DeckProvider(self.collection)
        # Cache validator lookups only within this request; no new persistent state.
        class CachedProvider:
            def __init__(self): self.cache = {}
            def get(self,key):
                if key not in self.cache: self.cache[key] = provider.get(key)
                return self.cache[key]
        validator = Lab(CachedProvider(),None)
        failures = set()
        for vector in sorted(vectors,key=score):
            counts = Counter()
            for fid,q in vector:
                ids = catalog[1].get(fid,[])
                counts[deck_identity(catalog[0][ids[0]]) if ids else fid] += q
            deck = Deck.model_construct(name='Archetype Composite',version='research',format='standard',notes='',
                cards=[DeckEntry.model_construct(card_id=fid,count=q) for fid,q in counts.items()])
            validation = validator.validate(deck)
            if validation['status']=='passes_supported_checks':
                cards, categories = self.deck_cards(dict(vector))
                return {**result,'status':'available','total':sum(dict(vector).values()),'cards':cards,'categories':categories}
            failures.update(validation['errors']+validation['unknown'])
        result['reasons']=['No observed candidate passed the current supported validation checks.',*sorted(failures)[:12]]
        return result
