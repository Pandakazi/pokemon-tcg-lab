"""Source-isolated normalized tournament evidence and deterministic analytics.

No upstream requests here. Cards and collection storage are never mutated.
Canonical identities are exactly the existing functional_signature + identity.
"""
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from .collection import identity, representative_printings
from .engine import functional_signature, normalized_name
from .limitless_main import SOURCE, PARSER_VERSION

ARCHETYPE_PREVALENCE_MIN_DECKS = 15


def percent(n, d):
    return round(100*n/d, 4) if d else None


class Competitive:
    def __init__(self, cards, path, format_start=None):
        self.cards, self.path = cards, Path(path).resolve()
        if self.path == cards.path:
            raise ValueError('Competitive storage must be separate from card storage')
        self.format_start = date.fromisoformat(format_start) if format_start else None

    def connect(self, write=False):
        if write:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path if write else self.path.as_uri()+'?mode=ro', uri=not write, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def initialize(self):
        with closing(self.connect(True)) as db, db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS competitive_events (
                source TEXT NOT NULL,id TEXT NOT NULL,date TEXT NOT NULL,raw TEXT NOT NULL,
                fetched_at TEXT NOT NULL,results INTEGER NOT NULL,published INTEGER NOT NULL,
                PRIMARY KEY(source,id));
              CREATE TABLE IF NOT EXISTS competitive_decks (
                source TEXT NOT NULL,event_id TEXT NOT NULL,rank INTEGER NOT NULL,
                resolved INTEGER NOT NULL,raw TEXT NOT NULL,cards TEXT NOT NULL,
                PRIMARY KEY(source,event_id,rank));
              CREATE TABLE IF NOT EXISTS competitive_pages (
                source TEXT NOT NULL,event_id TEXT NOT NULL,url TEXT NOT NULL,
                sha256 TEXT NOT NULL,parser TEXT NOT NULL,html TEXT NOT NULL,
                PRIMARY KEY(source,event_id,url));
              CREATE TABLE IF NOT EXISTS competitive_status (
                source TEXT PRIMARY KEY,error TEXT,checked_at TEXT NOT NULL);
            ''')

    def resolver(self):
        exact, names = defaultdict(set), defaultdict(set)
        with closing(self.cards.connect()) as db:
            sets = {r['id']:json.loads(r['raw']) for r in db.execute('SELECT id,raw FROM sets')}
            for r in db.execute("SELECT raw,set_id,number FROM cards WHERE game='tcg'"):
                card = json.loads(r['raw']); fid = identity(functional_signature(card))
                metadata = sets.get(r['set_id'], {})
                codes = [r['set_id'], metadata.get('tcgOnline'), metadata.get('abbreviation',{}).get('official')]
                for code in codes:
                    if isinstance(code,str):
                        exact[(code.upper(), str(r['number']).casefold().lstrip('0'))].add(fid)
                        # Main Limitless may use newer basic-Energy artwork not
                        # present in TCGdex yet (observed MEE 9–16). Use only a
                        # unique same-set, same-name basic Energy identity.
                        if card.get('category')=='Energy' and card.get('energyType')=='Normal':
                            exact[(code.upper(), 'basic:'+normalized_name(card['name']))].add(fid)
                names[normalized_name(card['name'])].add(fid)
        return exact, names

    def import_event(self, event, decks, results_count, pages, resolver=None, *, fetched_at=None):
        if event['format'] != 'standard' or date.fromisoformat(event['date']) > date.today():
            raise ValueError('Only completed international Standard events are eligible')
        exact, names = resolver or self.resolver()
        normalized = []
        for deck in decks:
            counts, unresolved = Counter(), []
            if sum(c['count'] for c in deck['cards']) != 60:
                raise ValueError('Invalid deck size; cache preserved')
            for c in deck['cards']:
                if type(c['count']) is not int or not 1 <= c['count'] <= 60:
                    raise ValueError('Invalid card count; cache preserved')
                key = (c['set'].upper(), str(c['number']).casefold().lstrip('0'))
                candidates = (exact.get(key) or exact.get((c['set'].upper(),'basic:'+normalized_name(c['name'])))
                              or names.get(normalized_name(c['name']), set()))
                if len(candidates) == 1:
                    counts[next(iter(candidates))] += c['count']
                else:
                    unresolved.append(c)
            normalized.append((deck, counts, unresolved))
        if len({d['rank'] for d in decks}) != len(decks) or results_count < len(decks):
            raise ValueError('Duplicate deck or invalid result coverage')
        self.initialize()
        now = fetched_at or datetime.now(timezone.utc).isoformat()
        with closing(self.connect(True)) as db, db:
            db.execute('DELETE FROM competitive_decks WHERE source=? AND event_id=?',(SOURCE,event['id']))
            db.execute('DELETE FROM competitive_pages WHERE source=? AND event_id=?',(SOURCE,event['id']))
            db.execute('INSERT OR REPLACE INTO competitive_events VALUES (?,?,?,?,?,?,?)',
                       (SOURCE,event['id'],event['date'],json.dumps(event),now,results_count,len(decks)))
            for deck, counts, unresolved in normalized:
                db.execute('INSERT INTO competitive_decks VALUES (?,?,?,?,?,?)',
                           (SOURCE,event['id'],deck['rank'],int(not unresolved),json.dumps({**deck,'unmapped_cards':unresolved}),json.dumps(counts)))
            for url, html in pages.items():
                db.execute('INSERT INTO competitive_pages VALUES (?,?,?,?,?,?)',
                           (SOURCE,event['id'],url,hashlib.sha256(html.encode()).hexdigest(),PARSER_VERSION,html))
        return {'published':len(decks),'mapped':sum(not r[2] for r in normalized)}

    def remap_cached(self):
        """Refresh normalization locally after card sync; retain fetch provenance."""
        events, decks, _ = self.evidence()
        resolver = self.resolver()
        reports = []
        for event in events:
            with closing(self.connect()) as db:
                pages = {r['url']:r['html'] for r in db.execute('SELECT url,html FROM competitive_pages WHERE source=? AND event_id=?',(SOURCE,event['id']))}
            reports.append(self.import_event(json.loads(event['raw']),[d['raw'] for d in decks if d['event_id']==event['id']],
                          event['results'],pages,resolver,fetched_at=event['fetched_at']))
        return reports

    def record_status(self, error=None):
        self.initialize()
        with closing(self.connect(True)) as db, db:
            db.execute('INSERT OR REPLACE INTO competitive_status VALUES (?,?,?)', (SOURCE,error,datetime.now(timezone.utc).isoformat()))

    def evidence(self):
        if not self.path.exists(): return [], [], None
        with closing(self.connect()) as db:
            events = [dict(r) for r in db.execute('SELECT * FROM competitive_events WHERE source=?',(SOURCE,))]
            decks = [{**dict(r),'raw':json.loads(r['raw']),'cards':json.loads(r['cards'])}
                     for r in db.execute('SELECT * FROM competitive_decks WHERE source=?',(SOURCE,))]
            status = db.execute('SELECT * FROM competitive_status WHERE source=?',(SOURCE,)).fetchone()
        return events, decks, dict(status) if status else None

    def stats(self, fid, window='30', today=None, include_trend=True, card_catalog=None):
        today = today or datetime.now(timezone.utc).date()
        if window not in ('7','30','90','format'): raise ValueError('Unsupported window')
        available = self.format_start is not None and self.format_start <= today
        start = self.format_start if window == 'format' else today-timedelta(days=int(window)-1)
        events, all_decks, source_status = self.evidence()
        dates = {e['id']:date.fromisoformat(e['date']) for e in events}
        selected = [e for e in events if start and start <= dates[e['id']] <= today]
        ids = {e['id'] for e in selected}
        decks = [d for d in all_decks if d['event_id'] in ids]
        eligible = [d for d in decks if d['resolved']]
        containing = [d for d in eligible if d['cards'].get(fid,0)>0]
        n, a = len(eligible), len(containing)
        error = source_status and source_status['error']
        state = ('format_unavailable' if window == 'format' and not available else
                 'observed' if n else 'mapping_failure' if decks else 'source_failure' if error else 'no_data')
        distribution = Counter(min(d['cards'][fid],4) for d in containing)
        field = Counter(d['raw']['archetype_id'] for d in eligible)
        played = Counter(d['raw']['archetype_id'] for d in containing)
        labels = {d['raw']['archetype_id']:d['raw']['archetype_name'] for d in eligible}
        archetypes = [dict(id=k,name=labels[k],decks=played[k],eligible_decks=field[k],
                           share_percent=percent(played[k],a),
                           prevalence_percent=percent(played[k],field[k]) if field[k]>=ARCHETYPE_PREVALENCE_MIN_DECKS and k!='unknown' else None,
                           status='unclassified' if k=='unknown' else 'observed' if field[k]>=ARCHETYPE_PREVALENCE_MIN_DECKS else 'insufficient_sample')
                      for k in sorted(field,key=lambda k:(-played[k],k))]
        overall = Counter(k for d in eligible for k in d['cards'])
        together = Counter(k for d in containing for k in d['cards'] if k!=fid)
        partners = []
        # Field association: >=5 A lists and >=3 joint lists; rank conservative
        # Wilson lower bound relative to B's field frequency, then lift and ID.
        for k, joint in together.items():
            if a < 5 or joint < 3: continue
            p = joint/a; z = 1.96
            lower = (p+z*z/(2*a)-z*((p*(1-p)+z*z/(4*a))/a)**.5)/(1+z*z/a)
            partners.append(dict(functional_id=k,decks=joint,cooccurrence_percent=percent(joint,a),
                                 field_percent=percent(overall[k],n),lift=round(p/(overall[k]/n),6),
                                 conservative_lift=round(lower/(overall[k]/n),6)))
        partners.sort(key=lambda p:(-p['conservative_lift'],-p['lift'],p['functional_id']))
        partners = partners[:20]
        if partners:
            references = representative_printings(self.cards,{p['functional_id'] for p in partners},card_catalog)
            for p in partners:
                p.update(references.get(p['functional_id'],dict(name='Unmapped card',printing_id=None,image_url=None)))
        trend = []
        trend_boundary = self.format_start if available else today-timedelta(days=89)
        points = sorted({d for d in dates.values() if trend_boundary<=d<=today})
        trend_start = self.format_start.isoformat() if available else points[0].isoformat() if points else None
        trend_end = today.isoformat() if available else points[-1].isoformat() if points else None
        if include_trend:
            # Plot actual event dates only; missing windows remain null, not zero.
            for key in ('7','30','90','format'):
                values = []
                for day in points:
                    begin = self.format_start if key=='format' else day-timedelta(days=int(key)-1)
                    ds = [d for d in all_decks if d['resolved'] and begin and begin <= dates[d['event_id']] <= day]
                    used = sum(bool(d['cards'].get(fid)) for d in ds)
                    values.append(dict(date=day.isoformat(),sample_size=len(ds),included_decks=used,usage_percent=percent(used,len(ds))))
                trend.append(dict(window=key,available=key!='format' or available,points=values))
        return dict(schema_version=1,source=SOURCE,source_label='Limitless',functional_id=fid,window=window,
                    archetype_prevalence_min_decks=ARCHETYPE_PREVALENCE_MIN_DECKS,
                    status=state,format_available=available,format_start=self.format_start.isoformat() if self.format_start else None,
                    period_start=start.isoformat() if start else None,period_end=today.isoformat(),sample_size=n,
                    included_decks=a,usage_percent=percent(a,n),average_copies=round(sum(d['cards'][fid] for d in containing)/a,4) if a else None,
                    copy_distribution=[dict(copies=f'{k}x' if k<4 else '4x+',decks=distribution[k],percent=percent(distribution[k],a)) for k in range(1,5)],
                    archetypes=archetypes,top_archetypes=[r for r in archetypes if r['decks']][:5],associated_cards=partners,
                    association_status='observed' if partners else 'insufficient_sample' if a<5 else 'no_qualifying_pairs',
                    trend=trend,trend_start=trend_start,trend_end=trend_end,
                    tournament_count=len(selected),published_decklists=len(decks),excluded_unmapped=len(decks)-n,
                    results_without_lists=sum(e['results']-e['published'] for e in selected),
                    last_updated=max((e['fetched_at'] for e in selected),default=None),source_error=error or None,
                    provenance=[{**json.loads(e['raw']),'fetched_at':e['fetched_at']} for e in selected],parser_version=PARSER_VERSION)
