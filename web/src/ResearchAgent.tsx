import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { useDeck } from './DeckBuilder'
import { useCompetitiveTimeframe } from './Competitive'

type Selected = {printing:string;name:string;identity?:string;variant?:string}
const Context = createContext<{selected:Selected|null;select:(card:Selected)=>void}>({selected:null,select:()=>{}})
export const useResearchAgent=()=>useContext(Context)
export function ResearchAgentProvider({children}:{children:ReactNode}) {
 const [selected,select]=useState<Selected|null>(null)
 return <Context.Provider value={{selected,select}}>{children}</Context.Provider>
}
type Status={version:string;available:boolean;reason:string|null;provider:string|null;model:string|null}
type Statement={text:string;evidence:string[]}
type Evidence={id:string;classification:string;payload:Record<string,unknown>;references:string[]}
type Reference={id:string;source:string;resource:string;url?:string;checked_at?:string;event_date?:string;content_hash:string}
type Result={status:string;reason?:string;answer:null|{outcome:string;facts:Statement[];interpretation:Statement[];limitations:string[]};
 envelope?:{content_hash:string;packet:{request:{printing:string;window:string;as_of:string};evidence:Evidence[];references:Reference[];coverage:{omitted:string[];unavailable:string[]}};
 active_deck:{id:string;name:string;revision:number;dirty:boolean;references:string[];[key:string]:unknown};omitted:string[]};
 execution?:{provider:string;model:string;latency_ms:number;input_tokens:number|null;output_tokens:number|null}}
const messages:Record<string,string>={
 busy:'Another research request is still running. No additional request was sent to a provider.',
 context_changed:'The deck changed. Review the current deck and submit again.',
 context_unavailable:'Card or active-deck evidence is unavailable. Open Deck Builder and select a card in the active deck.',
 selected_card_not_in_active_deck:'Select a card that is in the active deck.',
 inconsistent_snapshot:'Local evidence changed during retrieval. Submit again when updates finish.',
 budget_exceeded:'This context exceeds the evidence budget. No provider request was made.',
 output_token_limit_reached:'The response reached its output limit. No partial answer is shown.',
 provider_failure:'The provider did not return a usable completed response. No automatic retry was made.',
 invalid_answer_contract:'The response did not meet the answer or citation contract. No answer is shown.',
 internal_assessment_failure:'PokéLab could not assess the response. This is not a model-quality judgment.',
 internal_processing_failure:'PokéLab could not complete research processing.',
 request_timeout:'The research deadline expired. The provider request may still be finishing; no retry was made.',
 unavailable:'Research is not enabled or its configured provider is unavailable.',
 secret_input_rejected:'Research context could not be safely sent.',
}
function EvidenceValue({value}:{value:unknown}) {
 if(value===null||value===undefined)return <span>Unknown</span>
 if(Array.isArray(value))return value.length?<ul>{value.map((v,i)=><li key={i}><EvidenceValue value={v}/></li>)}</ul>:<span>None recorded</span>
 if(typeof value==='object')return <dl>{Object.entries(value).map(([k,v])=><div key={k}><dt>{k.replace(/_/g,' ')}</dt><dd><EvidenceValue value={v}/></dd></div>)}</dl>
 return <span>{String(value)}</span>
}
export function ResearchPanel({open,toggle}:{open:boolean;toggle:()=>void}) {
 const {selected}=useResearchAgent(),deck=useDeck(),{window:period}=useCompetitiveTimeframe()
 const [question,setQuestion]=useState(''),[status,setStatus]=useState<Status|null>(null),[statusError,setStatusError]=useState(false)
 const [pending,setPending]=useState(false),[result,setResult]=useState<Result|null>(null),[error,setError]=useState(''),[inspected,setInspected]=useState<string|null>(null)
 const [submitted,setSubmitted]=useState<{name:string;printing:string;variant?:string;question:string;revision:number;window:string}|null>(null)
 const flight=useRef(false),alive=useRef(true)
 useEffect(()=>{alive.current=true;return()=>{alive.current=false}},[])
 useEffect(()=>{
  if(!selected)return
  const controller=new AbortController();setStatus(null);setStatusError(false)
  fetch('/api/v1/agent/status',{signal:controller.signal}).then(async r=>{if(!r.ok)throw new Error();const s=await r.json();if(s.version!=='pokelab-research-v1')throw new Error();return s})
   .then(s=>{if(!controller.signal.aborted)setStatus(s)}).catch(()=>{if(!controller.signal.aborted)setStatusError(true)})
  return()=>controller.abort()
 },[selected])
 const entry=deck?.data?.deck.entries.find(e=>e.identity===selected?.identity)
 const ready=!!selected&&!!entry&&!!deck?.data&&!deck.pending&&!deck.error&&!!status?.available
 const ask=async()=>{
  if(flight.current||!ready||!question.trim()||!selected||!deck?.data)return
  flight.current=true;setPending(true);setResult(null);setError('');setInspected(null)
  const context={name:selected.name,printing:selected.printing,variant:selected.variant,question:question.trim(),revision:deck.data.revision,window:period};setSubmitted(context)
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),105000)
  try {
   const response=await fetch('/api/v1/agent/research',{method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,
    body:JSON.stringify({scope:'selected_card_research',question:context.question,printing:selected.printing,variant:selected.variant,revision:context.revision,window:period})})
   if(!response.ok)throw new Error()
   const value=await response.json() as Result
   if(typeof value.status!=='string'||!('answer' in value))throw new Error()
   if(alive.current)setResult(value)
  } catch {if(alive.current)setError('Research could not be received. The request may still be finishing. No automatic retry was made.')}
  finally {clearTimeout(timer);flight.current=false;if(alive.current)setPending(false)}
 }
 const stale=submitted&&(submitted.printing!==selected?.printing||submitted.variant!==selected?.variant||submitted.revision!==deck?.data?.revision||submitted.window!==period)
 const envelope=result?.envelope
 const evidence=inspected==='active-deck'?envelope?.active_deck:envelope?.packet.evidence.find(e=>e.id===inspected)
 const refs=evidence?.references as string[]|undefined
 const statements=(items:Statement[])=>items.map((s,i)=><div key={i} className="research-statement"><p>{s.text}</p><div>{s.evidence.map((id,n)=><button key={id} aria-label={`Inspect evidence ${id}`} onClick={()=>setInspected(id)}>Evidence {n+1}</button>)}</div></div>)
 return <aside className={`agent-panel research-agent ${open?'':'collapsed'}`} aria-label="PokéLab Agent">
  <button aria-label="Toggle Agent panel" aria-expanded={open} onClick={toggle}>{open?'PokéLab Agent ›':'‹'}</button>
  <div hidden={!open}>
   <h2>Research</h2><p>Read-only · selected-card research</p>
   {!selected?<p>Open Card Detail and choose “Ask about this card”.</p>:<>
    <div className="research-context" aria-label="Research context"><strong>{selected.name}</strong><span>{selected.printing}{selected.variant?` · ${selected.variant}`:''}</span><span>Active deck: {deck?.data?.deck.name||'Not loaded'}{deck?.data?.deck.dirty?' · draft':''}</span><span>Competitive window: {period==='format'?'Format':`${period} days`}</span></div>
    {!deck?.data?<p><Link to="/deck-builder">Open Deck Builder</Link> to load the active deck.</p>:!entry?<p>This card is not in the active deck.</p>:null}
    {!!deck?.pending&&<p>Waiting for deck changes to finish…</p>}
    {!!deck?.error&&<p>Resolve the active-deck error before asking.</p>}
    {statusError&&<p>Research status is unavailable. Select the card again after checking the API.</p>}
    {status&&!status.available&&<p>Research unavailable: {status.reason?.replace(/_/g,' ')}.</p>}
    {status?.model&&<p className="source-note">Configured: {status.provider} / {status.model}</p>}
    <form onSubmit={e=>{e.preventDefault();void ask()}}><label htmlFor="research-question">Question about this card</label><textarea id="research-question" maxLength={2000} value={question} onChange={e=>setQuestion(e.target.value)} placeholder="What role could this card play in my deck?"/>
     <button disabled={!ready||pending||!question.trim()}>Ask</button></form>
   </>}
   {pending&&<p role="status">Researching the submitted card and deck snapshot…</p>}
   {error&&<p role="alert">{error}</p>}
   {submitted&&(pending||result)&&<div className="research-context"><span>Submitted: {submitted.name} · revision {submitted.revision}</span><span>{submitted.question}</span>{stale&&<strong>Current context changed. This result belongs to the submitted snapshot.</strong>}</div>}
   {result&&!result.answer&&<p role="alert">{messages[result.status]||'Research could not produce a completed answer.'}{result.reason?` (${result.reason.replace(/_/g,' ')})`:''}</p>}
   {result?.answer&&<article aria-label="Research answer">
    {result.answer.outcome!=='answered'&&<p>{result.answer.outcome==='unsupported_question'?'This question is outside selected-card research.':'Available evidence is insufficient for a full answer.'}</p>}
    {!!result.answer.facts.length&&<section><h3>Evidence-backed facts</h3>{statements(result.answer.facts)}</section>}
    {!!result.answer.interpretation.length&&<section><h3>Plausible interpretation</h3><p>Interpretation is not evidence of the deck creator’s intent.</p>{statements(result.answer.interpretation)}</section>}
    <section><h3>What cannot be established</h3><ul>{result.answer.limitations.map((l,i)=><li key={i}>{l}</li>)}</ul></section>
   </article>}
   {envelope&&<details><summary>Evidence coverage and snapshot</summary><p>As of {envelope.packet.request.as_of}. Statistics retain the populations recorded below.</p><EvidenceValue value={{omitted:[...envelope.packet.coverage.omitted,...envelope.omitted],unavailable:envelope.packet.coverage.unavailable}}/>
    {envelope.packet.evidence.map(e=><button key={e.id} onClick={()=>setInspected(e.id)}>{String(e.payload.kind)}</button>)}<button onClick={()=>setInspected('active-deck')}>Active deck</button><p className="source-note">Evidence hash: {envelope.content_hash}</p></details>}
   {evidence&&<section aria-label="Inspected evidence" className="research-evidence"><h3>Evidence</h3><button onClick={()=>setInspected(null)}>Close evidence</button><EvidenceValue value={evidence}/>
    {envelope?.packet.references.filter(r=>refs?.includes(r.id)).map(r=><div key={r.id}><strong>{r.source}</strong><EvidenceValue value={r}/>{r.url&&/^https:\/\/(api\.tcgdex\.net|limitlesstcg\.com)\//.test(r.url)&&<a href={r.url} target="_blank" rel="noreferrer">Open source</a>}</div>)}</section>}
  </div>
 </aside>
}

