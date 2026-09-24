import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'
import { loadCollection, withOwnership, type VariationPage, type Ownership } from './api'
import { CardTile } from './CardTile'

export function CollectionPage() {
 const [params,setParams]=useSearchParams(),query=params.toString()
 const [data,setData]=useState<VariationPage|null>(null),[error,setError]=useState(''),[attempt,setAttempt]=useState(0),[view,setView]=useState<'gallery'|'list'>('gallery')
 useEffect(()=>{
  const controller=new AbortController();setError('')
  loadCollection(new URLSearchParams(query),controller.signal).then(r=>{if(!controller.signal.aborted)setData(r)}).catch(e=>{if(!controller.signal.aborted)setError(e.message)})
  return ()=>controller.abort()
 },[query,attempt])
 function update(key:string,value:string) {const next=new URLSearchParams(params);next.delete('page');value?next.set(key,value):next.delete(key);setData(null);setParams(next)}
 function changed(id:string,owned:Ownership) {setData(old=>old?{...old,cards:old.cards.map(c=>withOwnership(c,id,owned))}:old);setAttempt(v=>v+1)}
 return <main className="collection-page">
  <header className="collection-toolbar"><h1>Collection</h1><p>Owned exact printings and finishes · all formats</p>
   <label>Category <select value={params.get('category')||''} onChange={e=>update('category',e.target.value)}><option value="">All categories</option><option value="Pokemon">Pokémon</option><option value="Trainer">Trainers</option><option value="Energy">Energy</option></select></label>
   <label>Search collection <input value={params.get('q')||''} maxLength={100} onChange={e=>update('q',e.target.value)}/></label>
   <button aria-pressed={view==='gallery'} onClick={()=>setView('gallery')}>Gallery</button><button aria-pressed={view==='list'} onClick={()=>setView('list')}>List</button>
  </header>
  <section className="gallery-scroll" aria-label="Owned variations">
   {error && <p role="alert">{error} <button onClick={()=>setAttempt(v=>v+1)}>Retry</button></p>}
   {!data && !error && <p role="status">Loading collection…</p>}
   {data && !data.cards.length && <p>No owned variations match. Add cards from the Library or Card Detail.</p>}
   <div className={view==='gallery'?'card-grid':'card-list'}>{data?.cards.map(card=><CardTile key={`${card.id}:${card.ownership!.variant}`} card={card} exact list={view==='list'} onChange={changed}/>)}</div>
  </section>
  {data && <nav className="pagination"><button disabled={data.page<=1} onClick={()=>{const next=new URLSearchParams(params);next.set('page',String(data.page-1));setParams(next)}}>Previous</button><span>Page {data.page} of {Math.max(1,Math.ceil(data.total/data.page_size))} · {data.total} owned variations</span><button disabled={!data.next_page} onClick={()=>{const next=new URLSearchParams(params);next.set('page',String(data.next_page));setParams(next)}}>Next</button></nav>}
 </main>
}
