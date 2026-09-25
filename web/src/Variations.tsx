import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router'
import { loadVariations, savePreference, withOwnership, finishLabel, type Card, type Ownership, type VariationPage } from './api'
import { CardImage } from './CardTile'
import { MagnifiedArt } from './MagnifiedArt'
import { QuantityControls } from './QuantityControls'
import { useBuilder, detailPath, DeckControls } from './DeckBuilder'

export function Variations({id,library=false,onSelected,onChange,revision=0}:{id:string;library?:boolean;onSelected?:()=>void;onChange?:(id:string,o:Ownership)=>void;revision?:number}) {
 const location=useLocation()
 const builder=useBuilder()
 const [data,setData]=useState<VariationPage|null>(null),[page,setPage]=useState(1),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 useEffect(()=>{
  const controller=new AbortController();setData(null);setError('')
  loadVariations(id,library?'library':'functional',page,controller.signal).then(r=>{if(!controller.signal.aborted)setData(r)})
   .catch(e=>{if(!controller.signal.aborted)setError(e.message)})
  return ()=>controller.abort()
 },[id,library,page,revision])
 async function choose(card:Card) {
  setBusy(true);setError('')
  try{await savePreference(id,card);onSelected?.()}catch(e){setError(e instanceof Error?e.message:'Unable to save artwork.')}finally{setBusy(false)}
 }
 function changed(id:string,o:Ownership) {
  setData(old=>old?{...old,cards:old.cards.map(c=>withOwnership(c,id,o)),unassigned:old.unassigned?.map(c=>withOwnership(c,id,o))}:old);onChange?.(id,o)
 }
 return <section aria-label={library?'Library artwork choices':'Card variations'}>
  <p>{library?'Choose the printing and finish shown in your Library. This does not change ownership.':'All artwork stays full color. Inspecting a variation does not change Library artwork.'}</p>
  {error && <p role="alert">{error}</p>}
  {!data && !error && <p role="status">Loading variations…</p>}
  <div className="variation-grid">
   {data?.cards.map(card=><article className="variation-card" key={`${card.id}:${card.ownership!.variant}`} data-variation={`${card.id}:${card.ownership!.variant}`}>
    {library?<button disabled={busy} onClick={()=>choose(card)} aria-label={`Use ${card.id} ${finishLabel(card.ownership!.variant)} in Library`}><CardImage card={card}/></button>:
     <MagnifiedArt card={card}><Link to={`${detailPath(card.id,!!builder)}?variant=${encodeURIComponent(card.ownership!.variant)}`} state={{library:location.state?.library||(builder?'/deck-builder':'/')}} aria-label={`Inspect ${card.id} ${finishLabel(card.ownership!.variant)}`}><CardImage card={card}/></Link></MagnifiedArt>}
    <strong>{card.name}</strong><p>{card.set.name || card.set.id} · {card.localId}</p><code>{card.id}</code><p>{finishLabel(card.ownership!.variant)}</p>
    <small>{card.ownership!.quantity?`Owned ×${card.ownership!.quantity}`:'Not owned'}</small>
    {!library && (builder?<DeckControls card={card} presentation/>:<QuantityControls id={card.id} ownership={card.ownership!} onChange={changed}/>)}
   </article>)}
  </div>
  {!library && !!data?.unassigned?.length && <section className="unassigned-ownership" aria-label="Copies with no recorded finish"><h3>Copies with no recorded finish</h3><p>These existing copies are included in your total. They have not been assigned a finish.</p>
   {data.unassigned.map(card=><div key={card.id}><Link to={`${detailPath(card.id,!!builder)}?variant=unspecified`} state={{library:location.state?.library||(builder?'/deck-builder':'/')}}>{card.name} · {card.id}</Link>{builder?<><p>Owned: {card.ownership!.quantity}</p><DeckControls card={card}/></>:<QuantityControls id={card.id} ownership={card.ownership!} onChange={changed}/>}</div>)}
  </section>}
  {data && <nav className="pagination" aria-label="Variation pages"><button disabled={page<=1||busy} onClick={()=>setPage(p=>p-1)}>Previous variations</button><span>Page {page} of {Math.max(1,Math.ceil(data.total/data.page_size))}</span><button disabled={!data.next_page||busy} onClick={()=>setPage(p=>p+1)}>Next variations</button></nav>}
 </section>
}
