import {useEffect,useRef,useState} from 'react'
import {useDeck} from './DeckBuilder'
import {useCompetitiveTimeframe} from './Competitive'
import {EvidenceValue,ValidationDetails,messages,useResearchAgent} from './ResearchAgent'
import {ResearchCardText,type ResearchCard} from './ResearchCardText'

type Evidence={id:string;kind:'fact'|'evidence';title:string;printing?:string;value:Record<string,unknown>;[key:string]:unknown}
type Envelope={content_hash:string;selected:{printing:string;variant?:string}|null;revision:number|null;window:string;as_of:string;proof_requested:boolean;evidence:Evidence[];omissions:string[]}
type ProposedCard={card_id:string;printing_id:string;canonical_name:string;quantity:number;current_quantity?:number;validated?:boolean}
type Proposal={status:string;lifecycle:string;kind:string;name:string;source_revision:number|null;validation_status:string;legality_status:string;total_cards:number;cards:ProposedCard[];adds:ProposedCard[];removes:ProposedCard[];unresolved:{name:string;quantity:number;role:string}[];hard_validation:string[];strategic_diagnostics:string[];repair_notes:string[];alternatives:unknown[];premises:unknown[];limitations?:string[]}
type Result={status:string;conversation_id?:string;answer:null|{paragraphs:{text:string;evidence:string[]}[];facts:Evidence[];proposal?:Proposal};envelope?:Envelope;contract_diagnostics?:unknown;execution?:{provider:string;model:string;latency_ms:number}}
type Turn={question:string;result:Result;contextKey:string}

function AnswerView({result}:{result:Result}) {
 const [inspected,inspect]=useState<string|null>(null)
 const evidence=result.envelope?.evidence||[]
 const cards:ResearchCard[]=evidence.filter(e=>e.printing).map(e=>({id:e.id,name:e.title,printing:e.printing!}))
 const components:ResearchCard[]=[]
 for(const e of evidence)for(const key of ['attacks','abilities']){
  const values=e.value[key]
  if(Array.isArray(values))for(const c of values)if(c&&typeof c.name==='string'&&typeof c.effect==='string')components.push({id:e.id,name:c.name,printing:e.printing||'',printedText:c.effect})
 }
 // Ambiguous component names never silently resolve to a different printed effect.
 const aliases=[...cards,...components.filter(c=>components.filter(other=>other.name===c.name&&other.printedText!==c.printedText).length===0)]
 return <>
 {!result.answer&&<><p role="alert">{messages[result.status]||'No completed answer is available. No automatic retry was made.'}</p><ValidationDetails value={result.contract_diagnostics}/></>}
 {result.answer&&<article aria-label="Agent answer">
  {result.answer.proposal&&<ProposalView proposal={result.answer.proposal} cards={aliases} inspect={inspect}/>}
  {result.answer.paragraphs.map((p,i)=><p key={i}><ResearchCardText text={p.text} cards={aliases} inspect={inspect}/>{p.evidence.length>0&&<button className="source-note" aria-label={`Inspect support for paragraph ${i+1}`} onClick={()=>inspect(p.evidence[0])}> · evidence</button>}</p>)}
  {result.answer.facts.length>0&&<details><summary>Printed facts &amp; recorded evidence</summary>{result.answer.facts.map(e=><section key={e.id}><h3>{e.title}</h3><EvidenceValue value={e.value}/></section>)}</details>}
 </article>}
 {result.envelope&&<details className="research-evidence" open={result.envelope.proof_requested||!!inspected||undefined}>
  <summary>Evidence underneath</summary><p>Fact: local card/deck data. Evidence: recorded sources. Inference: the Agent’s strategic reasoning, not a proven result.</p>
  <p>Snapshot: {result.envelope.as_of} · {result.envelope.revision===null?'no active deck':`revision ${result.envelope.revision}`} · {result.envelope.window} window</p>
  {result.envelope.selected&&<p>{result.envelope.selected.printing} · {result.envelope.selected.variant}</p>}
  <p className="source-note">Evidence hash: {result.envelope.content_hash}</p>
  {evidence.map(e=><details key={e.id} open={inspected===e.id||undefined}><summary>{e.kind==='fact'?'Fact':'Evidence'} · {e.title}</summary><EvidenceValue value={e}/></details>)}
  {!evidence.length&&<p>No local facts were retrieved. This answer is general reasoning.</p>}
  <details><summary>Coverage boundaries</summary><EvidenceValue value={result.envelope.omissions}/><p>External research is unavailable. Nothing is saved or changed by the Agent.</p></details>
  {inspected&&<button onClick={()=>inspect(null)}>Close inspected evidence</button>}
 </details>}
 </>
}

function ProposalView({proposal:p,cards,inspect}:{proposal:Proposal;cards:ResearchCard[];inspect:(id:string)=>void}){
 const alternatives=p.alternatives.flatMap(group=>{
  if(!group||typeof group!=='object'||!('candidates' in group)||!Array.isArray(group.candidates))return []
  return group.candidates.flatMap(candidate=>candidate&&typeof candidate.canonical_name==='string'&&typeof candidate.printing_id==='string'?[{id:`alternative-${candidate.printing_id}`,name:candidate.canonical_name,printing:candidate.printing_id}]:[])
 })
 // Only unambiguous exact-printing alternatives receive a preview.
 const alternativeCards=alternatives.filter(c=>!alternatives.some(other=>other.name===c.name&&other.printing!==c.printing))
 const text=(s:string)=><ResearchCardText text={s} cards={cards} inspect={inspect}/>
 const alternativeText=(s:string)=><ResearchCardText text={s} cards={alternativeCards} inspect={()=>{}}/>
 return <section aria-label="Proposed deck review" className="research-context">
  <h3>{p.kind==='diff'?'Proposed changes':p.kind==='list'?'Proposed deck':'Card premise review'}{p.name?` · ${p.name}`:''}</h3>
  <p>Proposal only — nothing has been applied or saved.</p>
  {p.source_revision!==null&&<p>Source revision: {p.source_revision}</p>}
  {p.kind!=='premises'&&<><p>{p.total_cards} resolved cards · {p.validation_status==='VALIDATED'?'Passes supported construction checks':p.validation_status==='STALE'?'Source changed — needs review':p.lifecycle==='DRAFT'?'Partial shell — not a finished list':'Needs repair before use'}</p>
   {p.kind==='diff'&&(['removes','adds'] as const).map(key=><div key={key}><h3>{key==='removes'?'Proposed cuts':'Proposed additions'}</h3><ul>{p[key].map((c,i)=><li key={i}>{c.quantity} × {text(c.canonical_name)} · currently {c.current_quantity}{c.validated===false?' · cut not valid':''}</li>)}</ul></div>)}
   <details open={p.kind==='list'}><summary>{p.kind==='list'?'Resolved list':'Resulting proposed list'}</summary><ul>{p.cards.map((c,i)=><li key={i}>{c.quantity} × {text(c.canonical_name)} <small>{c.printing_id}</small></li>)}</ul></details>
   {!!p.unresolved.length&&<ul>{p.unresolved.map((c,i)=><li key={i}>{c.quantity} slots — {c.role||c.name} [unresolved]</li>)}</ul>}
  </>}
  {p.repair_notes.map((s,i)=><p key={i}>{text(s)}</p>)}
  {!!p.hard_validation.length&&<div><h3>Construction issues</h3><ul>{p.hard_validation.map((s,i)=><li key={i}>{text(s)}</li>)}</ul></div>}
  {!!p.strategic_diagnostics.length&&<div><h3>Strategic checks — advisory</h3><ul>{p.strategic_diagnostics.map((s,i)=><li key={i}>{text(s)}</li>)}</ul></div>}
  {!!p.alternatives.length&&<details><summary>Role-preserving alternatives</summary><EvidenceValue value={p.alternatives} renderString={alternativeText}/></details>}
  {!!p.premises.length&&<details><summary>Resolved card premises</summary><EvidenceValue value={p.premises}/></details>}
  <details><summary>Validation scope</summary><p>Legality: {p.legality_status.replace(/_/g,' ').toLowerCase()}. Strategic quality is a separate judgment.</p><EvidenceValue value={p.limitations}/></details>
 </section>
}

export function ConversationPanel({open,toggle}:{open:boolean;toggle:()=>void}) {
 const {selected,select}=useResearchAgent(),deck=useDeck(),{window}=useCompetitiveTimeframe()
 const [status,setStatus]=useState<{available:boolean;provider:string;model:string;reason?:string}|null>(null)
 const [statusError,setStatusError]=useState(false),[question,setQuestion]=useState(''),[turns,setTurns]=useState<Turn[]>([])
 const [includeDeck,setIncludeDeck]=useState(true),[pending,setPending]=useState(false),[error,setError]=useState('')
 const session=useRef<string|undefined>(undefined),flight=useRef(false),alive=useRef(true)
 const usesDeck=includeDeck&&!!deck?.data
 const contextKey=JSON.stringify([selected?.printing,selected?.variant,usesDeck?deck?.data?.revision:null,window])
 useEffect(()=>{alive.current=true;const controller=new AbortController()
  fetch('/api/v1/agent/status',{signal:controller.signal}).then(async r=>{if(!r.ok)throw new Error();return r.json()}).then(s=>{if(alive.current&&!controller.signal.aborted){setStatus(s);setStatusError(false)}}).catch(()=>{if(alive.current&&!controller.signal.aborted)setStatusError(true)})
  return()=>{alive.current=false;controller.abort()}
 },[])
 const ready=status?.available&&!pending&&(!usesDeck||!deck?.pending&&!deck?.error)
 const ask=async()=>{
  if(flight.current||!ready||!question.trim())return
  flight.current=true;setPending(true);setError('')
  const submitted=question.trim(),snapshot=contextKey
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),105000)
  try{
   const response=await fetch('/api/v1/agent/research',{method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,
    body:JSON.stringify({scope:'conversation',question:submitted,conversation_id:session.current,printing:selected?.printing,variant:selected?.variant,include_deck:usesDeck,revision:usesDeck?deck?.data?.revision:undefined,window})})
   if(!response.ok)throw new Error()
   const result:Result=await response.json()
   if(alive.current){if(result.conversation_id)session.current=result.conversation_id;setTurns(old=>[...old.slice(-11),{question:submitted,result,contextKey:snapshot}]);setQuestion('')}
  }catch{if(alive.current)setError(controller.signal.aborted?messages.request_timeout:'The request could not complete. No automatic retry was made.')}
  finally{clearTimeout(timer);flight.current=false;if(alive.current)setPending(false)}
 }
 return <aside className={`agent-panel research-agent conversation-agent ${open?'':'collapsed'}`} aria-label="PokéLab Agent">
  <button aria-label="Toggle Agent panel" aria-expanded={open} onClick={toggle}>{open?'PokéLab Agent ›':'‹'}</button>
  <div hidden={!open}><h2>Let’s talk Pokémon</h2><p>Explore ideas, compare cards, or talk through a plan.</p>
   <p className="source-note">Read-only · One request per Ask · This conversation lasts only in this session.</p>
   <button disabled={pending} onClick={()=>{session.current=undefined;setTurns([]);setQuestion('');setError('')}}>New conversation</button>
   {selected&&<div className="research-context">{selected.name} · {selected.printing} · {selected.variant}<button onClick={()=>select(null)}>Clear selected card</button></div>}
   {deck?.data&&<label className="research-deck-option"><input type="checkbox" checked={includeDeck} onChange={e=>setIncludeDeck(e.target.checked)}/>Use active deck: {deck.data.deck.name} · revision {deck.data.revision}</label>}
   {status?.model&&<p className="source-note">Configured: {status.provider} / {status.model}</p>}
   {status&&!status.available&&<p>Agent unavailable: {status.reason?.replace(/_/g,' ')}.</p>}
   {statusError&&<p role="alert">Agent status unavailable. Check the API and reload.</p>}
   {turns.map((t,i)=><section className="conversation-turn" key={i}><h3>You</h3><p>{t.question}</p><h3>PokéLab</h3>{t.contextKey!==contextKey&&<p className="source-note">Earlier snapshot — current context has changed.</p>}<AnswerView result={t.result}/></section>)}
   {pending&&<p role="status">Thinking with the submitted context…</p>}{error&&<p role="alert">{error}</p>}
   <form onSubmit={e=>{e.preventDefault();void ask()}}><label htmlFor="conversation-question">Ask PokéLab</label><textarea id="conversation-question" maxLength={2000} value={question} onChange={e=>setQuestion(e.target.value)} placeholder="What would you like to explore?"/><button disabled={!ready||!question.trim()}>Ask</button></form>
  </div>
 </aside>
}
