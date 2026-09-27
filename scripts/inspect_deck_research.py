"""Explicit local paths only. Produces immutable profile/packet plus a PM summary."""
import argparse
from datetime import date
from pathlib import Path
from pokelab.agent_context import canonical
from pokelab.agent_context_sources import Sources
from pokelab.deck_research import build_profile, select_evidence


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('cards','collection','workspace','competitive','archetype','output'):
        parser.add_argument('--'+key,required=True)
    parser.add_argument('--revision',type=int,required=True)
    parser.add_argument('--as-of',type=date.fromisoformat,required=True)
    parser.add_argument('--question',required=True)
    parser.add_argument('--active-observation')
    args=parser.parse_args()
    sources=Sources(**{k:getattr(args,k) for k in ('cards','collection','workspace','competitive')})
    profile=build_profile(sources,revision=args.revision,as_of=args.as_of,archetype=args.archetype,active_observation=args.active_observation)
    packet=select_evidence(profile,args.question)
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    (output/'profile.json').write_text(canonical(profile)+'\n',encoding='utf-8')
    (output/'packet.json').write_text(canonical(packet)+'\n',encoding='utf-8')
    pop=profile.population
    lines=['# Deterministic Dragapult inspection (no AI interpretation)',
        '',f'Deck: {profile.name}; revision {profile.revision}; total {profile.total}.',
        'Categories: '+', '.join(f'{f.field}={f.value}' for f in profile.categories)+'.',
        f'Comparison: {pop.name}; explicit local archetype {pop.archetype}; {pop.window}-day window; as-of {pop.as_of}.',
        f'Eligible mapped lists: {pop.eligible_lists}; published {pop.published_lists}; excluded unmapped {pop.excluded_unmapped}; excluded current identity {pop.excluded_current_identity}.',
        f'Exact-vector observation matches: {len(profile.matching_observations)}. Matches are not proof of copied-deck provenance or creator intent.',
        f'Self-comparison: {pop.self_comparison}; reason {pop.self_comparison_reason}; excluded {pop.excluded_self}.',
        '', 'Complete composition:']
    lines += [f'- {c.name}: {c.quantity} ({c.identity})' for c in profile.cards if c.quantity]
    for label in ('ARCHETYPE_CORE','UNCOMMON_PRESENT','COMMON_ABSENT','ABOVE_TYPICAL_QUANTITY','BELOW_TYPICAL_QUANTITY'):
        lines+=['',label+':']
        rows=[r for r in profile.comparisons if label in r.characteristics]
        lines += [f'- {r.name}: active {r.active_quantity}; included {r.lists_including}/{r.eligible_lists}; typical band {r.typical_range}; observed range {r.observed_range}; distribution '+', '.join(f'{b.quantity}:{b.lists}' for b in r.distribution) for r in rows[:5]] or ['- None observed under the documented rule.']
    names={c.identity:c.name for c in profile.cards}
    lines+=['',f'Question: {args.question}',f'Intent: {", ".join(packet.intent.categories)}','Selected evidence, in order:']
    lines += [f'- {e.kind}: {names.get(e.identity,"deck/population")} [{e.classification}]' for e in packet.evidence]
    lines += ['',f'Packet bytes: {packet.serialized_bytes}/24576.',f'Packet hash: `{packet.content_hash}`.',
        f'Profile hash: `{profile.content_hash}`.','Omitted: '+', '.join(packet.coverage.omitted),
        'Unavailable: '+', '.join(packet.coverage.unavailable),
        '', 'Population list URLs, dates, fetched-at metadata and content hashes are retained in profile.json. packet.json is the exact bounded serialization; trailing file newline is not part of packet bytes/hash.',
        'This is a local snapshot inspection, not a reconstruction of provider output.']
    (output/'inspection.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'profile={profile.content_hash} packet={packet.content_hash} bytes={packet.serialized_bytes}')


if __name__=='__main__': main()
