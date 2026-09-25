import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { Link, useLocation, useSearchParams } from 'react-router'
import { useBuilder, detailPath } from './DeckBuilder'
import { AssociatedCardPreview } from './AssociatedCardPreview'

type Window = '7'|'30'|'90'|'format'
type Archetype = {id:string;research_id?:string;name:string;decks:number;eligible_decks:number;share_percent:number|null;prevalence_percent:number|null;status:string}
type Point = {date:string;usage_percent:number|null;sample_size:number;included_decks:number}
export type Research = {
 schema_version:1;source:'limitless-main';window:Window;status:string;archetype_prevalence_min_decks:number;format_available:boolean;format_start:string|null
 period_start:string|null;period_end:string;usage_percent:number|null;average_copies:number|null;included_decks:number;sample_size:number
 tournament_count:number;published_decklists:number;excluded_unmapped:number;results_without_lists:number;last_updated:string|null;source_error:string|null
 top_archetypes:Archetype[];archetypes:Archetype[];copy_distribution:{copies:string;decks:number;percent:number|null}[]
 associated_cards:{functional_id:string;name:string;printing_id?:string|null;image_url?:string|null;decks:number;cooccurrence_percent:number;field_percent:number;lift:number}[];association_status:string
 trend:{window:Window;available:boolean;points:Point[]}[];trend_start?:string|null;trend_end?:string|null;parser_version:string
 provenance:{id:string;name:string;url:string;date:string;fetched_at:string}[]
}
const Windows = createContext<{window:Window;setWindow:(value:Window)=>void}>({window:'30',setWindow:()=>{}})
export function CompetitiveProvider({children}:{children:ReactNode}) {
 const [remembered,setRemembered]=useState<Window>('30'),[params,setParams]=useSearchParams(),location=useLocation()
 const requested=params.get('window'),window=(['7','30','90','format'].includes(requested||'')?requested:remembered) as Window
 const setWindow=(value:Window)=>{setRemembered(value);if(location.pathname!=='/'&&location.pathname!=='/deck-builder'&&location.pathname!=='/collection'){const next=new URLSearchParams(params);next.set('window',value);next.delete('page');setParams(next,{state:location.state})}}
 return <Windows.Provider value={{window,setWindow}}>{children}</Windows.Provider>
}
export const useCompetitiveTimeframe=()=>useContext(Windows)
export function ArchetypeLink({archetype,children}:{archetype:Archetype;children?:ReactNode}) {
 const builder=useBuilder(),location=useLocation(),{window}=useContext(Windows)
 return archetype.research_id?<Link to={`${builder?'/deck-builder':''}/archetypes/${archetype.research_id}?window=${window}${children?'#tournament-evidence':''}`} state={{researchFrom:location.pathname+location.search,researchFromState:location.state}}>{children||archetype.name}</Link>:<>{children||archetype.name}</>
}
const label=(w:Window)=>w==='format'?'Format':`${w}D`
const decimal=(n:number|null)=>n===null?'Unavailable':String(Number(n.toFixed(2)))
const decklists=(n:number)=>`${n} decklist${n===1?'':'s'}`
const pct=(n:number|null)=>n===null?'Unavailable':`${Number(n.toFixed(2))}%`
function useResearch(id:string,enabled=true,trend=true) {
 const {window}=useContext(Windows)
 const [data,setData]=useState<Research|null>(null),[error,setError]=useState('')
 useEffect(()=>{
  setData(null);setError('');if(!enabled)return
  const controller=new AbortController()
  fetch(`/api/v1/competitive/cards/${encodeURIComponent(id)}?window=${window}&source=limitless-main&trend=${trend}`,{signal:controller.signal})
   .then(async response=>{if(!response.ok)throw new Error('Competitive source or mapping unavailable.');const result=await response.json();if(result.schema_version!==1||result.source!=='limitless-main')throw new Error('Unexpected competitive source response.');if(!Number.isInteger(result.archetype_prevalence_min_decks)||result.archetype_prevalence_min_decks<1||!Array.isArray(result.associated_cards)||result.associated_cards.some((p:object)=>!('image_url' in p)||!('printing_id' in p)))throw new Error('The competitive API is out of date. Restart the PokéLab API, then reload this page.');return result as Research})
   .then(result=>{if(!controller.signal.aborted)setData(result)})
   .catch(reason=>{if(!controller.signal.aborted)setError(reason.message)})
  return ()=>controller.abort()
 },[id,enabled,window,trend])
 return {data,error,window}
}
export function CompetitiveWindows({formatAvailable}:{formatAvailable?:boolean}) {
 const {window,setWindow}=useContext(Windows)
 return <div role="group" aria-label="Competitive timeframe" className="competitive-windows"><span>Competitive timeframe</span>{(['7','30','90','format'] as Window[]).map(w=><button key={w} aria-pressed={window===w} disabled={w==='format'&&formatAvailable===false} title={w==='format'&&formatAvailable===false?'Configure an explicit format start date to enable Format.':undefined} onClick={()=>setWindow(w)}>{label(w)}</button>)}</div>
}
function State({data,error}:{data:Research|null;error:string}) {
 if(error)return <p role="alert">{error}</p>
 if(!data)return <p role="status">Loading competitive evidence…</p>
 const messages:Record<string,string>={no_data:'No competitive data available.',mapping_failure:'Mapping failure — published lists could not be fully mapped.',source_failure:'Source failure — tournament evidence could not be loaded.',format_unavailable:'Format unavailable — configure an explicit format start date.'}
 return <>{messages[data.status]&&<p role="status">{messages[data.status]}</p>}{data.source_error&&<p role="alert">Last ingestion failed. Cached evidence may be incomplete or stale. {data.source_error}</p>}</>
}
function Sample({data}:{data:Research}) {
 return <p className="source-note">{data.sample_size.toLocaleString()} analyzed/mapped decklists · {data.tournament_count} tournaments<br/>
 <span title="Any list with an unresolved card is excluded in full so an unknown mapping cannot count as absence.">{data.excluded_unmapped} unmapped/excluded lists</span> · <span title="Published results without a decklist never enter the usage denominator.">{data.results_without_lists} results without lists</span></p>
}
export function useCompetitiveHover(enabled:boolean) {
 const [open,setOpen]=useState(false),[position,setPosition]=useState({left:0,top:0})
 const delay=useRef<ReturnType<typeof setTimeout>|undefined>(undefined), grace=useRef<ReturnType<typeof setTimeout>|undefined>(undefined)
 const clear=()=>{clearTimeout(delay.current);clearTimeout(grace.current)}
 useEffect(()=>()=>clear(),[])
 useEffect(()=>{if(!open)return;const close=(event:Event)=>{if(event.type==='scroll'&&event.target instanceof Element&&event.target.closest('.competitive-popup'))return;clear();setOpen(false)};window.addEventListener('scroll',close,true);window.addEventListener('resize',close);return()=>{window.removeEventListener('scroll',close,true);window.removeEventListener('resize',close)}},[open])
 const enter=(element:HTMLElement)=>{
  if(!enabled||element.tagName!=='IMG')return;clearTimeout(grace.current);if(open)return
  clearTimeout(delay.current)
  delay.current=setTimeout(()=>{const rect=element.getBoundingClientRect();setPosition({left:Math.max(8,Math.min(rect.left,window.innerWidth-338)),top:Math.max(8,Math.min(rect.bottom+6,window.innerHeight-440))});setOpen(true)},500)
 }
 const leave=()=>{clearTimeout(delay.current);clearTimeout(grace.current);grace.current=setTimeout(()=>setOpen(false),180)}
 return {open,position,enter,leave,keep:()=>clearTimeout(grace.current),close:()=>{clear();setOpen(false)}}
}
export function CompetitivePopup({id,name,deckIdentity,hover}:{id:string;name:string;deckIdentity?:string;hover:ReturnType<typeof useCompetitiveHover>}) {
 const builder=useBuilder(),location=useLocation()
 const {data,error,window}=useResearch(id,hover.open,false)
 if(!hover.open)return null
 return createPortal(<aside role="dialog" aria-label={`${name} competitive preview`} className="competitive-popup" style={hover.position} onPointerEnter={hover.keep} onPointerLeave={hover.leave} onFocus={hover.keep} onBlur={hover.leave} onKeyDown={e=>{if(e.key==='Escape')hover.close()}}>
  <strong>{name}</strong>{builder?.data&&deckIdentity&&<p><strong>{(()=>{const n=builder.data.deck.entries.find(e=>e.identity===deckIdentity)?.quantity||0;return `${n} ${n===1?'Card':'Cards'} in deck`})()}</strong></p>}<p>Competitive • {window==='format'?'Current Format':`Last ${window} Days`}</p><State data={data} error={error}/>
  {data&&<><dl><dt>Usage</dt><dd>{pct(data.usage_percent)}</dd><dt>Average copies</dt><dd>{decimal(data.average_copies)}</dd></dl>
   <h3>Top five archetypes</h3><ol>{data.top_archetypes.slice(0,5).map(a=><li key={a.id}><ArchetypeLink archetype={a}/> <span>{pct(a.share_percent)}</span></li>)}</ol>{!data.top_archetypes.length&&<p>No archetype observations.</p>}<Sample data={data}/></>}
  <p>Source: Limitless</p><Link to={detailPath(id,!!builder)} state={{library:location.pathname+location.search}} onClick={hover.close}>Click for full research →</Link>
 </aside>,document.body)
}
const colors:Record<Window,string>={'7':'#60a5fa','30':'#fbbf24','90':'#f472b6',format:'#34d399'}
export function UsageTrend({series,start,end}:{series:Research['trend'];start?:string|null;end?:string|null}) {
 const [hidden,setHidden]=useState<Window[]>([]),[point,setPoint]=useState<string|null>(null)
 const dates=[...new Set(series.flatMap(s=>s.points.map(p=>p.date)))].sort()
 const first=start||dates[0],last=end||dates.at(-1)
 const min=Date.parse(first||'2000-01-01'),max=Date.parse(last||'2000-01-01')
 const x=(d:string)=>55+(Date.parse(d)-min)/Math.max(86400000,max-min)*700
 const y=(v:number)=>215-v*1.85
 return <><div className="trend-legend">{series.map(s=><button key={s.window} style={{borderColor:colors[s.window]}} disabled={!s.available} aria-pressed={!hidden.includes(s.window)} onClick={()=>setHidden(old=>old.includes(s.window)?old.filter(w=>w!==s.window):[...old,s.window])}>{label(s.window)}{!s.available?' unavailable':''}</button>)}</div>
 {!dates.length?<p>No dated competitive evidence available.</p>:<svg className="usage-trend" viewBox="0 0 800 260" role="img" aria-label="Usage trend: rolling 7D, 30D, 90D and cumulative Format">
 {[0,25,50,75,100].map(v=><g key={v}><line x1="55" x2="755" y1={y(v)} y2={y(v)} stroke="currentColor" opacity=".15"/><text x="4" y={y(v)+4} fill="currentColor" fontSize="12">{v}%</text></g>)}
 {series.filter(s=>s.available&&!hidden.includes(s.window)).map((s,i)=>{let pen=false;const path=s.points.map(p=>{if(p.usage_percent===null){pen=false;return ''}const command=pen?'L':'M';pen=true;return `${command}${x(p.date)},${y(p.usage_percent)}`}).join(' ');return <g key={s.window} data-series={s.window}><path d={path} fill="none" stroke={colors[s.window]} strokeWidth="2.5" strokeDasharray={i===0?undefined:i===1?'8 3':i===2?'3 3':'12 3 3 3'}/>{s.points.filter(p=>p.usage_percent!==null).map(p=><circle key={p.date} cx={x(p.date)} cy={y(p.usage_percent!)} r="5" fill={colors[s.window]} tabIndex={0} onMouseEnter={()=>setPoint(p.date)} onFocus={()=>setPoint(p.date)} aria-label={`${label(s.window)} ${p.date}: ${pct(p.usage_percent)} of ${p.sample_size} eligible decklists`}><title>{label(s.window)} · {p.date}: {pct(p.usage_percent)} · {p.included_decks}/{p.sample_size} eligible decklists</title></circle>)}</g>})}
 <text x="55" y="245" fill="currentColor" fontSize="12">{first}</text><text x="755" y="245" textAnchor="end" fill="currentColor" fontSize="12">{last}</text>
 </svg>}
 {point&&<div className="trend-point" aria-live="polite">{point}{series.filter(s=>!hidden.includes(s.window)).map(s=>{const p=s.points.find(p=>p.date===point);return <span key={s.window}>{label(s.window)}: {p?.usage_percent===null||p?.usage_percent===undefined?'Unavailable':`${pct(p.usage_percent)}`} · {p?.sample_size??0} eligible decklists</span>})}</div>}
 <p className="source-note">Rolling calendar-day windows; Format is cumulative from the configured start. Points are observed event dates; connecting lines are guides, not additional observations. Empty samples remain unavailable.</p></>
}
export function CompetitiveDashboard({id}:{id:string}) {
 const {data,error}=useResearch(id)
 return <section className="competitive-dashboard" aria-label="Competitive research"><h2>Competitive research</h2><CompetitiveWindows formatAvailable={data?.format_available}/><State data={data} error={error}/>
 {data&&<>
  <section><h3>Competitive Overview</h3><dl><dt>Usage</dt><dd>{pct(data.usage_percent)}</dd><dt>Average copies in decks using card</dt><dd>{decimal(data.average_copies)}</dd><dt>Decks using card</dt><dd>{data.included_decks}</dd><dt>Eligible sample</dt><dd>{data.sample_size}</dd></dl></section>
  <section><h3>Copy Distribution</h3><p>Among decks using this functional card.</p><ul className="copy-distribution">{data.copy_distribution.map(d=><li key={d.copies}><strong>{d.copies}</strong> {pct(d.percent)} · {d.decks} decks</li>)}</ul></section>
  <section><h3>Usage Trend</h3><UsageTrend series={data.trend} start={data.trend_start} end={data.trend_end}/></section>
  <section><h3>Archetypes</h3><p>Where played: share of decks containing this card. Prevalence: share within the archetype; at least {data.archetype_prevalence_min_decks} eligible archetype decklists required.</p>
   {!data.archetypes.length?<p>No archetype observations.</p>:<div className="research-table"><table><thead><tr><th>Archetype</th><th>Where played</th><th>Prevalence within archetype</th><th>Eligible decks</th></tr></thead><tbody>{data.archetypes.map(a=><tr key={a.id}><th><ArchetypeLink archetype={a}/></th><td>{pct(a.share_percent)}</td><td>{a.status==='insufficient_sample'?`Insufficient sample for prevalence — ${decklists(a.eligible_decks)}`:a.status==='unclassified'?'Unclassified':pct(a.prevalence_percent)}</td><td>{a.eligible_decks}{a.eligible_decks>0&&a.research_id&&<p><ArchetypeLink archetype={a}>Explore {a.eligible_decks} decks →</ArchetypeLink></p>}</td></tr>)}</tbody></table></div>}</section>

  <section><h3>Associated Cards</h3><p>Co-occurrence is the percentage of decks using this card that also use the associated card. Lift compares that frequency with the overall eligible field. It does not establish causation.</p>
   {data.associated_cards.length?<div className="research-table"><table><thead><tr><th>Card</th><th>Co-occurrence</th><th>Field usage</th><th>Association / lift</th><th>Joint decks</th></tr></thead><tbody>{data.associated_cards.map(p=><tr key={p.functional_id}><th><AssociatedCardPreview name={p.name} imageUrl={p.image_url}/></th><td>{pct(p.cooccurrence_percent)}</td><td>{pct(p.field_percent)}</td><td>{p.lift.toFixed(2)}×</td><td>{p.decks}</td></tr>)}</tbody></table></div>:<p>{data.association_status==='insufficient_sample'?`Insufficient sample — ${data.included_decks} decks using this card`:'No pairs meet the sample safeguards.'}</p>}
   <p className="source-note">Minimum 5 decks using this card and 3 joint observations. Ordered by conservative association (95% Wilson lower bound / field frequency), then lift.</p></section>
  <section><h3>Evidence / Dataset</h3><p>Source: <a href="https://limitlesstcg.com/tournaments" target="_blank" rel="noreferrer">Limitless tournament database</a> · {label(data.window)} · {data.period_start??'Start unavailable'} through {data.period_end}</p><Sample data={data}/><p>Last updated: {data.last_updated??'Not yet ingested'}<br/>Published lists: {data.published_decklists}<br/>Format start: {data.format_start??'Not configured'}</p>
   <p>Usage = fully mapped published lists containing this functional card / all fully mapped published lists in the selected window. This is a cached sample of international Standard tournament results, not all tournament entrants. Unknown archetypes remain in the field denominator.</p>
   <details><summary>Tournament provenance</summary><ul>{data.provenance.map(e=><li key={e.id}><a href={e.url} target="_blank" rel="noreferrer">{e.name}</a> · {e.date} · fetched {e.fetched_at}</li>)}</ul></details></section>
 </>}
 </section>
}
