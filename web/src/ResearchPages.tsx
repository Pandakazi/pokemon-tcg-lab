import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router'
import type { Card } from './api'
import { CardTile } from './CardTile'
import { CompetitiveWindows, useCompetitiveTimeframe } from './Competitive'
import { useBuilder, useDeck, type CopySource } from './DeckBuilder'

type Reference={functional_id:string;card:Card|null;owned:number}
type Counted=Reference&{quantity:number}
type Stat=Reference&{included_decks:number;eligible_decks:number;inclusion_percent:number|null;total_copies:number;average_when_included:number;average_all_decks:number;median_copies:number;distribution:{quantity:number;decks:number}[]}
type Observation={id:string;event_id:string;event:string;date:string;player:string;placement:number;archetype_id:string;archetype:string;source_url:string|null;event_url:string;mapped:boolean;fetched_at:string}
type Summary={id:string;name:string;source_id:string;window:string;status:string;format_available:boolean;format_start:string|null;period_start:string|null;period_end:string;evidence_start:string|null;evidence_end:string|null;eligible_decks:number;published_decks:number;excluded_unmapped:number;tournament_count:number;results_without_lists:number;results_without_lists_scope:string;prevalence_min_decks:number;source_error:string|null;provenance:{id:string;name:string;url:string;date:string;fetched_at:string}[]}
type Composite={label:string;algorithm:string;status:string;sample_size:number;limited_evidence:boolean;total:number;categories:Record<string,number>;cards:Counted[];reasons:string[];limitations:string[]}
type Evidence={total:number;page:number;next_page:number|null;decks:Observation[]}
type Published={name:string;set:string;number:string;count:number}
type Tournament={observation:Observation;card_count:number;mapped_card_count:number;categories:Record<string,number>;cards:Counted[];published_cards:Published[];unmapped_cards:Published[];pages:{url:string;sha256:string;parser:string}[];presentation_note:string}
const decimal=(n:number)=>Number(n.toFixed(2))
const scrollMemory=new Map<string,number>()
async function read<T>(url:string,signal:AbortSignal):Promise<T>{const response=await fetch(url,{signal});if(!response.ok)throw new Error(response.status===404?'This research identity was not found in local evidence.':'Local research evidence is unavailable. Retry after checking the API.');return response.json()}

function useResearchPage(){
 const {key=''}=useParams(),location=useLocation(),builder=useBuilder(),[params,setParams]=useSearchParams(),{window}=useCompetitiveTimeframe()
 const prefix=builder?'/deck-builder':'',path=location.pathname+location.search
 const main=useRef<HTMLElement>(null)
 const state={researchFrom:path,researchFromState:location.state}
 const change=(name:string,value:string)=>{const next=new URLSearchParams(params);next.set(name,value);if(name==='excluded')next.delete('page');setParams(next,{state:location.state})}
 const back=typeof location.state?.researchFrom==='string'?location.state.researchFrom:prefix||'/'
 return {key,location,builder,params,window,prefix,path,main,state,change,back,view:params.get('view')==='list'?'list' as const:'gallery' as const}
}
function Modes({view,change}:{view:string;change:(name:string,value:string)=>void}){return <div className="research-modes" aria-label="Research view">{['gallery','list'].map(v=><button key={v} aria-pressed={view===v} onClick={()=>change('view',v)}>{v==='gallery'?'Gallery':'List'}</button>)}</div>}
function Totals({categories,total}:{categories:Record<string,number>;total:number}){return <p className="research-totals"><strong>{total} cards</strong> · Pokémon {categories.Pokemon||0} · Trainers {categories.Trainer||0} · Energy {categories.Energy||0}{!!categories.Unknown&&` · Unknown ${categories.Unknown}`}</p>}
function EvidenceCard({row,list}:{row:Reference;list:boolean}){return <>{row.card?<CardTile card={row.card} list={list} competitive readOnly/>:<p>Card mapping unavailable · {row.functional_id}</p>}<small>Owned: {row.owned} across this functional card</small></>}
function Cards({cards,view}:{cards:Counted[];view:string}){return <div className={`research-cards ${view}`}>
 {cards.map(row=><div className="research-card" key={row.functional_id}><strong className="research-quantity">×{row.quantity}</strong><EvidenceCard row={row} list={view==='list'}/></div>)}
 </div>}

function CopyResearch({source,eligible,label}:{source:CopySource;eligible:boolean;label:string}){
 const deck=useDeck(),navigate=useNavigate(),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 useEffect(()=>{if(eligible&&deck&&!deck.data&&!deck.pending&&!deck.error)deck.reload()},[eligible,deck?.data,deck?.pending,deck?.error])
 const copy=async()=>{
  if(!deck?.data||busy)return
  const discard=deck.data.deck.dirty
  if(discard&&!window.confirm('Discard unsaved changes to the active draft and open a new copied deck? Existing saved decks are kept. Cancel to save your draft first.'))return
  setBusy(true);setError('')
  try{await deck.copyResearch(source,discard);navigate('/deck-builder')}
  catch(e){setError(e instanceof Error?e.message:'Copy failed. Reload the active deck before retrying.')}
  finally{setBusy(false)}
 }
 return <div className="research-copy"><button disabled={!eligible||!deck?.data||!!deck?.pending||!!deck?.error||busy} onClick={copy}>{busy?'Copying…':label}</button>
  {!eligible&&<p>A complete, representable 60-card list is required to copy.</p>}
  {(error||deck?.error)&&<p role="alert">{error||deck?.error} <button disabled={busy||!!deck?.pending} onClick={()=>{setError('');deck?.reload()}}>Reload active deck</button></p>}
 </div>
}

export function ArchetypeResearch(){
 const ctx=useResearchPage(),{key,window,params,path,main,prefix,state,change,view}=ctx
 const page=Math.max(1,Number(params.get('page'))||1),excluded=params.get('excluded')==='1'
 const [data,setData]=useState<{summary:Summary;stats:Stat[];composite:Composite;evidence:Evidence}|null>(null),[error,setError]=useState(''),[attempt,setAttempt]=useState(0)
 const requestKey=`${key}:${window}:${page}:${excluded}`,resolved=useRef('')
 useEffect(()=>{
  const controller=new AbortController();setData(null);setError('')
  const base=`/api/v1/research/archetypes/${encodeURIComponent(key)}`,query=`window=${window}`
  Promise.all([read<Summary>(`${base}?${query}`,controller.signal),read<{cards:Stat[]}>(`${base}/cards?${query}`,controller.signal),read<Composite>(`${base}/composite?${query}`,controller.signal),read<Evidence>(`${base}/decks?${query}&page=${page}&include_excluded=${excluded}`,controller.signal)])
   .then(([summary,stats,composite,evidence])=>{if(!controller.signal.aborted){resolved.current=requestKey;setData({summary,stats:stats.cards,composite,evidence})}})
   .catch(e=>{if(!controller.signal.aborted)setError(e.message)})
  return()=>controller.abort()
 },[requestKey,attempt])
 const loaded=resolved.current===requestKey?data:null
 useEffect(()=>{if(loaded&&main.current){main.current.scrollTop=scrollMemory.get(path)||0;if(!scrollMemory.has(path)&&ctx.location.hash==='#tournament-evidence')main.current.querySelector('#tournament-evidence')?.scrollIntoView()}},[loaded,path])
 return <main ref={main} className="research-page" onScroll={e=>{if(loaded)scrollMemory.set(path,e.currentTarget.scrollTop)}}>
  <Link to={ctx.back} state={ctx.location.state?.researchFromState}>← Back to research context</Link><h1>{loaded?.summary.name||'Archetype Research'}</h1>
  <CompetitiveWindows formatAvailable={loaded?.summary.format_available}/>
  {error?<p role="alert">{error} <button onClick={()=>setAttempt(n=>n+1)}>Retry</button></p>:!loaded?<p role="status">Loading archetype evidence…</p>:<>
   <p>Limitless · {window==='format'?'Format':`${window}D`} · {loaded.summary.period_start||'Start unavailable'} through {loaded.summary.period_end}</p>
   <p>{loaded.summary.eligible_decks} eligible analyzed/mapped decklists · {loaded.summary.tournament_count} tournaments · Observed dates: {loaded.summary.evidence_start||'None'} — {loaded.summary.evidence_end||'None'}</p>
   {loaded.summary.status==='format_unavailable'?<p role="status">Format start not configured or unavailable.</p>:loaded.summary.eligible_decks===0?<p role="status">No mapped decks in timeframe.</p>:loaded.summary.eligible_decks<loaded.summary.prevalence_min_decks&&<p>Limited evidence — {loaded.summary.eligible_decks} published decklists. Insufficient sample for prevalence.</p>}
   {loaded.summary.source_error&&<p role="alert">Last source refresh failed: {loaded.summary.source_error}. Showing cached evidence.</p>}
   <Modes view={view} change={change}/>
   <section aria-label="Archetype Composite"><h2>Archetype Composite</h2><p>Deterministic analytical synthesis — not an actual tournament deck, an AI-generated deck, or a claim of optimality.</p>
    <CopyResearch key={`${key}:${window}`} source={{source:'composite',key,window}} eligible={loaded.composite.status==='available'&&loaded.composite.total===60&&loaded.composite.cards.every(c=>!!c.card)} label="Copy Composite to Deck Builder"/>
    <p>{loaded.composite.limited_evidence?'Limited evidence — ':''}Composite based on {loaded.composite.sample_size} published decklists · {window==='format'?'Format':`${window}D`}</p>
    {loaded.composite.status==='available'?<><Totals categories={loaded.composite.categories} total={loaded.composite.total}/><Cards cards={loaded.composite.cards} view={view}/></>:<><p>Composite unavailable from current evidence.</p><ul>{loaded.composite.reasons.map(r=><li key={r}>{r}</li>)}</ul></>}
    <details><summary>Method and limitations</summary><p>We select the supported-check-valid observed quantity vector with the smallest total absolute copy-count distance to every eligible entrant. Ties favor common cards, then stable functional IDs and quantities. Whole observed vectors retain 60 cards and observed structure; cards are never independently rounded or invented. The result can match an observed list, but is presented as analytical synthesis.</p>{loaded.composite.limitations.map(r=><p key={r}>{r}</p>)}<p>Copy creates a new editable deck using local preferred printings. Research evidence stays unchanged.</p></details>
   </section>
   <section aria-label="Core cards"><h2>Observed cards</h2><p>Ordered by decks containing the functional card, then total copies. Artwork is representative; source finish is not inferred.</p>
    <div className={`research-cards ${view}`}>{loaded.stats.map(row=><div className="research-card" key={row.functional_id}><EvidenceCard row={row} list={view==='list'}/>
     <p>{row.inclusion_percent===null?(loaded.summary.source_id==='unknown'?'Unclassified — prevalence unavailable':`Insufficient sample for prevalence — ${row.eligible_decks} decklists`):`${decimal(row.inclusion_percent)}% of analyzed archetype decks`} · {row.included_decks}/{row.eligible_decks} included</p>
     <p>Average {decimal(row.average_when_included)} copies when included · {decimal(row.average_all_decks)} across all decks · Median {decimal(row.median_copies)}</p>
     <details><summary>Quantity distribution</summary>{row.distribution.map(b=><p key={b.quantity}>{b.quantity} copies: {b.decks} decks</p>)}</details>
    </div>)}</div>
   </section>
   <section id="tournament-evidence" aria-label="Tournament decks"><h2>Tournament decks</h2><p>Actual published tournament observations. Entrants sharing a list remain separate.</p>
    <label><input type="checkbox" checked={excluded} onChange={e=>change('excluded',e.target.checked?'1':'0')}/> Include unmapped/excluded lists</label>
    <p>{loaded.evidence.total} {excluded?'published':'eligible mapped'} decks</p>
    {!loaded.evidence.decks.length&&<p>No published lists available on this page.</p>}
    <ul className="evidence-list">{loaded.evidence.decks.map(d=><li key={d.id}><Link to={`${prefix}/tournament-decks/${d.id}?window=${window}&view=${view}`} state={state}>{d.player} · {d.event} · #{d.placement}</Link><span>{d.date} · {d.archetype} · {d.mapped?'Mapped':'Some cards could not be mapped'}</span></li>)}</ul>
    <nav className="pagination" aria-label="Evidence pages"><button disabled={page<=1} onClick={()=>change('page',String(page-1))}>Previous decks</button><span>Page {page}</span><button disabled={!loaded.evidence.next_page} onClick={()=>change('page',String(page+1))}>Next decks</button></nav>
   </section>
   <section><h2>Evidence / Dataset</h2><p>{loaded.summary.published_decks} published archetype lists · {loaded.summary.excluded_unmapped} unmapped/excluded lists. Excluded lists never enter prevalence or composite calculations.</p><p>{loaded.summary.results_without_lists} results without lists. {loaded.summary.results_without_lists_scope}</p><p>Format start: {loaded.summary.format_start||'Not configured'}</p>
    <details><summary>Tournament provenance</summary>{loaded.summary.provenance.map(e=><p key={e.id}><a href={e.url} target="_blank" rel="noreferrer">{e.name}</a> · {e.date} · fetched {e.fetched_at}</p>)}</details>
   </section>
  </>}
 </main>
}

export function TournamentDeckResearch(){
 const ctx=useResearchPage(),{key,window,path,main,prefix,state,view,change}=ctx
 const [data,setData]=useState<Tournament|null>(null),[error,setError]=useState(''),[attempt,setAttempt]=useState(0),resolved=useRef('')
 useEffect(()=>{const controller=new AbortController();setData(null);setError('');read<Tournament>(`/api/v1/research/tournament-decks/${encodeURIComponent(key)}`,controller.signal).then(r=>{if(!controller.signal.aborted){resolved.current=key;setData(r)}}).catch(e=>{if(!controller.signal.aborted)setError(e.message)});return()=>controller.abort()},[key,attempt])
 const loaded=resolved.current===key?data:null
 useEffect(()=>{if(loaded&&main.current)main.current.scrollTop=scrollMemory.get(path)||0},[loaded,path])
 return <main ref={main} className="research-page" onScroll={e=>{if(loaded)scrollMemory.set(path,e.currentTarget.scrollTop)}}><Link to={ctx.back} state={ctx.location.state?.researchFromState}>← Back to research context</Link><h1>Tournament Deck Research</h1>
  {error?<p role="alert">{error} <button onClick={()=>setAttempt(n=>n+1)}>Retry</button></p>:!loaded?<p role="status">Loading tournament deck…</p>:<>
   <p className="source-note">ACTUAL OBSERVED TOURNAMENT DECK · LIMITLESS</p><h2>{loaded.observation.player} · #{loaded.observation.placement}</h2><p>{loaded.observation.event} · {loaded.observation.date}</p>
   <p>Archetype: <Link to={`${prefix}/archetypes/${loaded.observation.archetype_id}?window=${window}`} state={state}>{loaded.observation.archetype}</Link></p>
   <p>{loaded.presentation_note}</p><Totals categories={loaded.categories} total={loaded.card_count}/>
   <CopyResearch key={key} source={{source:'tournament',key,window}} eligible={loaded.observation.mapped&&loaded.card_count===60&&loaded.mapped_card_count===60&&!loaded.unmapped_cards.length&&loaded.cards.every(c=>!!c.card)} label="Copy to Deck Builder"/>
   {!loaded.observation.mapped&&<p role="status">Some cards could not be mapped. Showing {loaded.mapped_card_count} mapped copies; this list is excluded from aggregate statistics. Original published lines remain below.</p>}
   <Modes view={view} change={change}/><Cards cards={loaded.cards} view={view}/>
   <section><h2>Published source list</h2><p>Original names, set codes, numbers and quantities. Source finish is not established.</p><ul>{loaded.published_cards.map((c,i)=><li key={i}>{c.count} × {c.name} · {c.set} {c.number}</li>)}</ul>
   {!!loaded.unmapped_cards.length&&<><h3>Unmapped source lines</h3><ul>{loaded.unmapped_cards.map((c,i)=><li key={i}>{c.count} × {c.name} · {c.set} {c.number}</li>)}</ul></>}
   </section>
   <section><h2>Evidence / Dataset</h2><p>Observation ID: <code>{loaded.observation.id}</code> · Event {loaded.observation.event_id}, placement {loaded.observation.placement}</p><p>Fetched: {loaded.observation.fetched_at}</p>{loaded.observation.source_url&&<p><a href={loaded.observation.source_url} target="_blank" rel="noreferrer">View source on Limitless</a></p>}
    <details><summary>Archived source pages / hashes</summary>{loaded.pages.map(p=><p key={p.url}><a href={p.url} target="_blank" rel="noreferrer">Source page</a> · {p.parser}<br/><code>{p.sha256}</code></p>)}</details><p>Copy creates a new editable deck. Source quantities remain unchanged; local printings and finishes are presentation choices.</p>
   </section>
  </>}
 </main>
}
