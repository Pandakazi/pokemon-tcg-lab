import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router'
import { finishLabel, type Card, type Ownership } from './api'

type Allocation = {printing_id:string;variant:string;quantity:number;available:boolean;owned:Ownership|null}
type Entry = {identity:string;quantity:number;allocations:Allocation[];printing_id:string;variant:string;name:string;category:string;presentation_available:boolean;owned:Ownership|null}
export type Workspace = {schema_version:2;runtime_revision?:string;defaults:Record<string,{printing_id:string;variant:string;available:boolean}>;revision:number;deck:{id:string;name:string;format:string;entries:Entry[];has_saved:boolean;dirty:boolean};validation:{state:'EMPTY'|'IN PROGRESS'|'VALID'|'INVALID';total:number;categories:Record<string,number>;reasons:string[];unknown:string[];limitations:string[]};saved:{id:string;name:string;updated_at:string}[]}
type Command = {action:'quantity'|'remove'|'default_printing'|'rename'|'save'|'new'|'open';printing_id?:string;variant?:string;identity?:string;delta?:number;name?:string;deck_id?:string;discard?:boolean;exact?:boolean}
type Context = {data:Workspace|null;error:string;pending:number;send:(command:Command)=>void;reload:()=>void;active:boolean}
const DeckContext=createContext<Context|null>(null)
export const useDeck=()=>useContext(DeckContext)
export const useBuilder=()=>{const context=useDeck();return context?.active?context:null}
export const detailPath=(id:string,builder:boolean)=>`${builder?'/deck-builder':''}/cards/${encodeURIComponent(id)}`

async function request(command?:Command,revision?:number):Promise<Workspace> {
 const response=await fetch('/api/v1/deck-workspace',command?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...command,schema_version:2,revision})}:undefined)
 const data=await response.json()
 if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Unable to store deck changes. Reload the stored draft before continuing.')
 if(data.schema_version!==2||!Number.isInteger(data.revision)||!data.defaults||!data.deck?.entries?.every((e:Entry)=>Array.isArray(e.allocations)))throw new Error('Deck API is out of date. Restart the API and reload.')
 return data
}
export function DeckProvider({children}:{children:ReactNode}) {
 const location=useLocation(),active=location.pathname.startsWith('/deck-builder')
 const [data,setData]=useState<Workspace|null>(null),[error,setError]=useState(''),[pending,setPending]=useState(0)
 const current=useRef<Workspace|null>(null),queue=useRef(Promise.resolve()),blocked=useRef(false),loading=useRef(false)
 const apply=(value:Workspace)=>{current.current=value;setData(value)}
 const reload=()=>{
  if(loading.current)return
  loading.current=true;setPending(n=>n+1)
  queue.current=queue.current.then(async()=>{try{apply(await request());blocked.current=false;setError('')}catch(e){setError(e instanceof Error?e.message:'Unable to load deck.');blocked.current=true}finally{loading.current=false;setPending(n=>n-1)}})
 }
 useEffect(()=>{if(active&&!current.current&&!loading.current&&!blocked.current)reload()},[active])
 useEffect(()=>{
  const warn=(e:BeforeUnloadEvent)=>{if(pending){e.preventDefault();e.returnValue=''}}
  window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)
 },[pending])
 const send=(command:Command)=>{
  if(blocked.current||!current.current)return
  setPending(n=>n+1)
  queue.current=queue.current.then(async()=>{
   try{if(!blocked.current)apply(await request(command,current.current!.revision))}
   catch(e){blocked.current=true;setError(`${e instanceof Error?e.message:'Deck update failed.'} Further queued edits were stopped. Reload the stored draft to reconcile before continuing.`)}
   finally{setPending(n=>n-1)}
  })
 }
 return <DeckContext.Provider value={{data,error,pending,send,reload,active}}>{children}</DeckContext.Provider>
}

export function ReadOnlyOwnership({card,detail=false}:{card:Card;detail?:boolean}) {
 const owned=card.ownership
 if(!owned)return <p>Ownership unavailable</p>
 return <div className="deck-ownership"><strong>OWNED</strong> <span>{detail?owned.quantity:owned.library_total}</span>
  {detail&&<><p>{finishLabel(owned.variant)} — this variation: {owned.quantity}</p><p>Function total: {owned.functional_total}</p></>}
 </div>
}
export function DeckControls({card,exact=false,detail=false}:{card:Card;exact?:boolean;detail?:boolean}) {
 const builder=useBuilder()
 if(!builder)return null
 const {data,error,send}=builder,key=card.deck_identity
 const entry=data?.deck.entries.find(e=>e.identity===key),total=entry?.quantity||0
 const quantity=exact?(entry?.allocations.find(a=>a.printing_id===card.id&&a.variant===card.ownership?.variant)?.quantity||0):total
 const change=(delta:number)=>send({action:'quantity',printing_id:card.id,variant:card.ownership?.variant,delta,exact})
 return <div className="deck-card-controls">
  {!exact&&<span>{detail?'Add to deck':'In deck'}</span>}
  <div className="deck-stepper"><button disabled={!data||!!error||!quantity||!key} aria-label={`Remove ${card.name} from deck`} onClick={()=>change(-1)}>−</button>
   <output aria-label={`${card.name} deck quantity`}>{quantity}</output>
   <button disabled={!data||!!error||!key} aria-label={`Add ${card.name} to deck`} onClick={()=>change(1)}>+</button></div>
  {!key&&<small>Restart the API to enable deck controls.</small>}
  {exact&&<small>Total in deck: {total}</small>}
 </div>
}

export function DeckTray() {
 const builder=useBuilder(),location=useLocation()
 const [opening,setOpening]=useState(false),[renaming,setRenaming]=useState(false),[name,setName]=useState('')
 if(!builder)return null
 const {data,error,pending,send,reload}=builder
 const switchDeck=(action:'new'|'open',deck_id?:string)=>{
  if(data?.deck.dirty&&!window.confirm('Discard changes to the active draft? Cancel to save it first.'))return
  send({action,deck_id,discard:!!data?.deck.dirty});setOpening(false)
 }
 return <aside className="deck-tray" aria-label="Active deck">
  <header><h2>Active deck</h2>{data&&<><h3>{data.deck.name}</h3><span>Standard</span></>}
   <div className="deck-actions"><button disabled={!data||!!pending||!!error||renaming} onClick={()=>switchDeck('new')}>New</button>
    <button disabled={!data||!!pending||!!error||renaming} onClick={()=>setOpening(v=>!v)}>Open</button>
    <button disabled={!data||!!pending||!!error||renaming} onClick={()=>send({action:'save'})}>Save</button>
    <button disabled={!data||!!pending||!!error||renaming} onClick={()=>{setOpening(false);setName(data!.deck.name);setRenaming(true)}}>Rename</button></div>
   {renaming&&<form onSubmit={e=>{e.preventDefault();if(name.trim()){send({action:'rename',name});setRenaming(false)}}}><input aria-label="Deck name" autoFocus maxLength={100} value={name} onChange={e=>setName(e.target.value)}/><button disabled={!name.trim()||!!pending||!!error}>Apply name</button><button type="button" onClick={()=>setRenaming(false)}>Cancel</button></form>}
   {opening&&<div className="deck-open" aria-label="Saved decks">{data?.saved.length?data.saved.map(d=><button key={d.id} onClick={()=>switchDeck('open',d.id)}>{d.name}</button>):<p>No saved decks yet.</p>}</div>}
  </header>
  {error&&<div role="alert"><p>{error}</p><button disabled={!!pending} onClick={reload}>Reload stored draft</button></div>}
  {!data&&!error&&<p role="status">Loading deck…</p>}
  {data&&<><section className="deck-validation" aria-label="Deck validation">
   <strong>{data.validation.total} / 60</strong> <span className={`deck-state state-${data.validation.state.replace(/ /g,'-').toLowerCase()}`}>{data.validation.state}</span>
   <p>Pokémon {data.validation.categories.Pokemon||0} · Trainers {data.validation.categories.Trainer||0} · Energy {data.validation.categories.Energy||0}</p>
   {data.validation.state==='IN PROGRESS'&&<p>{60-data.validation.total} cards remaining</p>}
   {!!data.validation.reasons.length&&<ul>{data.validation.reasons.map(r=><li key={r}>{r}</li>)}</ul>}
   {!!data.validation.unknown.length&&<details open><summary>Legality needs verification</summary><ul>{data.validation.unknown.map(r=><li key={r}>{r}</li>)}</ul></details>}
   {!!data.validation.limitations.length&&<details><summary>Supported checks</summary>{data.validation.limitations.map(r=><p key={r}>{r}</p>)}</details>}
  </section>
  <div className="deck-entries">{!data.deck.entries.length&&<p>Choose cards from the Library to begin.</p>}
   {['Pokemon','Trainer','Energy'].map(category=>{const entries=data.deck.entries.filter(e=>e.category===category);return entries.length?<section key={category}><h3>{category==='Pokemon'?'Pokémon':category}</h3>{entries.map(entry=><article key={entry.identity}>
    <Link to={`${detailPath(entry.printing_id,true)}?variant=${encodeURIComponent(entry.variant)}`} state={{library:location.pathname==='/deck-builder'?location.pathname+location.search:location.state?.library||'/deck-builder'}} title={entry.name}>{entry.name}</Link>
    {entry.allocations.map(a=><small key={`${a.printing_id}:${a.variant}`}><Link to={`${detailPath(a.printing_id,true)}?variant=${encodeURIComponent(a.variant)}`} state={{library:location.state?.library||'/deck-builder'}}>{a.printing_id} · {finishLabel(a.variant)}</Link> ×{a.quantity}{!a.available?' · Presentation unavailable':''}</small>)}
    <div className="deck-stepper"><button disabled={!!error||!entry.presentation_available} aria-label={`Decrease ${entry.name} in tray`} onClick={()=>send({action:'quantity',printing_id:entry.printing_id,variant:entry.variant,delta:-1})}>−</button><output>{entry.quantity}</output><button disabled={!!error||!entry.presentation_available} aria-label={`Increase ${entry.name} in tray`} onClick={()=>send({action:'quantity',printing_id:entry.printing_id,variant:entry.variant,delta:1})}>+</button><button disabled={!!error} aria-label={`Remove all ${entry.name}`} onClick={()=>send({action:'remove',identity:entry.identity})}>Remove</button></div>
    <small>Owned (function): {entry.owned?.functional_total??'unknown'} · Ownership does not limit deck building</small>
   </article>)}</section>:null})}
  </div><footer role="status">{pending?'Storing changes…':data.deck.dirty?'Draft stored · changes not saved to named deck':data.deck.has_saved?'Saved':'New draft'}<button disabled={!!pending} onClick={reload} aria-label="Refresh active deck">↻</button></footer></>}
 </aside>
}
