"""Narrow main-Limitless HTML adapter. Never imported by a request-time fetcher.

Observed markup: tournaments data-* rows, result rows and text decklist cards.
Any missing/duplicate/mismatched structure aborts the event, preserving its cache.
"""
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
import re

SOURCE = 'limitless-main'
ORIGIN = 'https://limitlesstcg.com'
PARSER_VERSION = 'main-html-v1'


class SourceLayoutError(ValueError):
    pass


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def find(self, tag=None, cls=None):
        result = []
        for child in self.children:
            if isinstance(child, Node):
                if (tag is None or child.tag == tag) and (cls is None or cls in child.attrs.get('class', '').split()):
                    result.append(child)
                result.extend(child.find(tag, cls))
        return result

    def text(self):
        return ' '.join(' '.join(c.text() if isinstance(c, Node) else c for c in self.children).split())


class Tree(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node('root'); self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs)); self.stack[-1].children.append(node)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]; break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def require(condition, message):
    if not condition:
        raise SourceLayoutError(f'Limitless source layout/validation failure: {message}')


def one(nodes, description):
    require(len(nodes) == 1, description)
    return nodes[0]


def parse_index(html):
    root = Tree(html).root
    table = one(root.find('table', 'data-table'), 'tournament table')
    rows = [r for r in table.find('tr') if r.find('td')]
    require(rows, 'empty tournament index')
    events = []
    for row in rows:
        a = row.attrs
        require(all(a.get(k) for k in ('data-date','data-format','data-name','data-players')), 'index row attributes')
        try:
            day = date.fromisoformat(a['data-date']); players = int(a['data-players'])
        except ValueError as exc:
            raise SourceLayoutError('Invalid tournament date/player count') from exc
        links = [x.attrs['href'] for x in row.find('a') if re.fullmatch(r'/tournaments/\d+', x.attrs.get('href',''))]
        url = one(links, 'event link')
        events.append(dict(id=url.rsplit('/',1)[1], name=a['data-name'], date=day.isoformat(),
                           format=a['data-format'], players=players, url=ORIGIN+url))
    require(len({e['id'] for e in events}) == len(events), 'duplicate tournaments')
    pagination = one(root.find('ul', 'pagination'), 'index pagination')
    try:
        current, maximum = int(pagination.attrs['data-current']), int(pagination.attrs['data-max'])
    except (KeyError, ValueError) as exc:
        raise SourceLayoutError('Invalid index pagination') from exc
    require(1 <= current <= maximum, 'pagination bounds')
    return events, current, maximum


def parse_results(html):
    root = Tree(html).root
    table = one(root.find('table', 'data-table'), 'results table')
    rows = [r for r in table.find('tr') if r.find('td')]
    require(rows, 'empty results')
    result = {}
    for row in rows:
        a = row.attrs
        require(all(k in a for k in ('data-rank','data-name','data-deck')), 'result row attributes')
        require(a['data-rank'].isdigit() and a['data-name'], 'result rank/player')
        rank = int(a['data-rank'])
        require(rank > 0 and rank not in result, 'duplicate/invalid placement')
        lists = [x.attrs['href'] for x in row.find('a') if re.fullmatch(r'/decks/list/\d+', x.attrs.get('href',''))]
        decks = [x.attrs['href'] for x in row.find('a') if re.fullmatch(r'/decks/\d+(?:\?variant=\d+)?', x.attrs.get('href',''))]
        require(len(lists) <= 1 and len(decks) <= 1, 'ambiguous deck links')
        result[rank] = dict(rank=rank, player=a['data-name'], archetype_name=a['data-deck'] or 'Uncategorized',
                            archetype_id=decks[0] if decks else 'unknown', list_url=ORIGIN+lists[0] if lists else None)
    # A published list URL may be shared by multiple players. The competitive
    # unit is their distinct event/result entry, not a deduplicated list URL.
    return result


def parse_decklists(html, results):
    root = Tree(html).root
    section = one(root.find('section','tournament-decklists'), 'decklists section')
    output = {}
    for block in section.find('div','tournament-decklist'):
        toggle = one(block.find('div','decklist-toggle'), 'decklist placement toggle')
        match = re.fullmatch(r'decklist-(\d+)', toggle.attrs.get('data-target',''))
        require(match, 'decklist rank')
        rank = int(match[1])
        require(rank in results and results[rank]['list_url'] and rank not in output, 'unexpected/duplicate decklist')
        cards = []
        for card in block.find('div','decklist-card'):
            a = card.attrs
            require(a.get('data-set') and a.get('data-number') and a.get('data-lang') == 'en', 'card printing attributes/language')
            count = one(card.find('span','card-count'), 'card count').text()
            name = one(card.find('span','card-name'), 'card name').text()
            require(count.isdigit() and 1 <= int(count) <= 60 and name, 'invalid card count/name')
            cards.append(dict(set=a['data-set'], number=a['data-number'], name=name, count=int(count)))
        require(sum(c['count'] for c in cards) == 60, 'published list is not 60 cards')
        output[rank] = {**results[rank], 'cards':cards}
    require(set(output) == {r for r, v in results.items() if v['list_url']}, 'published list coverage mismatch')
    return list(output.values())
