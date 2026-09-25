import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams, useSearchParams } from 'react-router'
import { loadDetail, classification, withOwnership, type Detail, type Ownership } from './api'
import { MagnifiedArt } from './MagnifiedArt'
import { QuantityControls } from './QuantityControls'
import { Variations } from './Variations'
import { CompetitiveDashboard } from './Competitive'
import { useBuilder, ReadOnlyOwnership, DeckControls } from './DeckBuilder'

export function CardDetail() {
 const {printingId=''}=useParams()
 const location=useLocation()
 const builder=useBuilder()
 const [params]=useSearchParams(),variant=params.get('variant')||undefined
 const [variationsOpen,setVariationsOpen]=useState(false),[revision,setRevision]=useState(0)
 const [data,setData]=useState<Detail|null>(null), [error,setError]=useState(''), [attempt,setAttempt]=useState(0)
 const title=useRef<HTMLHeadingElement>(null)
 useEffect(()=>{
  const controller=new AbortController();setData(null);setError('')
  loadDetail(printingId,controller.signal,variant).then(result=>{if(!controller.signal.aborted)setData(result)})
   .catch(reason=>{if(!controller.signal.aborted)setError(reason instanceof Error?reason.message:'Unable to load this printing.')})
  return ()=>controller.abort()
 },[printingId,variant,attempt])
 useEffect(()=>{if(data)title.current?.focus()},[data?.card.id,data?.card.ownership?.variant])
 const card=data?.card.id===printingId?data.card:undefined
 function changed(id:string,owned:Ownership) {setData(old=>old?{...old,card:withOwnership(old.card,id,owned)}:old)}
 return <main className="detail-page">
  <Link to={location.state?.library || (builder?'/deck-builder':'/')} state={location.state?.libraryState}>← Back to {/\/(archetypes|tournament-decks)\//.test(location.state?.library||'')?'research':builder?'Deck Builder':'library'}</Link>
  {!card && !error && <p role="status">Loading card…</p>}
  {error && <div role="alert"><h1>Card could not be loaded</h1><p>{error}</p><button onClick={()=>setAttempt(v=>v+1)}>Retry</button></div>}
  {card && data && <>
   <div className="detail-layout"><div className="detail-art"><MagnifiedArt key={card.id} card={card}/>
    {builder?<><ReadOnlyOwnership card={card} detail/><DeckControls card={card} detail/></>:card.ownership && <><QuantityControls id={card.id} ownership={card.ownership} onChange={(id,o)=>{changed(id,o);setRevision(v=>v+1)}}/>
     <p>Functional total: <output aria-label="Functional total" aria-live="polite">{card.ownership.functional_total}</output></p></>}
    {card.ownership && <button className="detail-variations-toggle" aria-expanded={variationsOpen} aria-controls="detail-variations" onClick={()=>setVariationsOpen(v=>!v)}>Variations</button>}
   </div>
    <section><p className="source-note">CARD DETAILS · EXACT PRINTING</p><h1 ref={title} tabIndex={-1}>{card.name}</h1>
     <p>{classification(card)}</p><dl>
      <dt>Printing ID</dt><dd><code>{card.id}</code></dd>
      <dt>Set</dt><dd>{card.set.name || card.set.id} ({card.set.id}{card.set.code?` / ${card.set.code}`:''})</dd>
      <dt>Collector number</dt><dd>{card.localId}</dd>
      {card.rarity && <><dt>Rarity</dt><dd>{card.rarity}</dd></>}
      {card.regulationMark && <><dt>Regulation mark</dt><dd>{card.regulationMark}</dd></>}
      {card.evolveFrom && <><dt>Evolves from</dt><dd>{card.evolveFrom}</dd></>}
      {card.suffix && <><dt>Rule-box label</dt><dd>{card.suffix}</dd></>}
      {card.illustrator && <><dt>Illustrator</dt><dd>{card.illustrator}</dd></>}
     </dl>
     <h2>Card text</h2>
     {card.abilities?.map((a,i)=><section className="rule-text" key={`ability-${i}`}><h3>{a.type || 'Ability'}{a.name?` — ${a.name}`:''}</h3><p>{a.effect}</p></section>)}
     {card.attacks?.map((a,i)=><section className="rule-text" key={`attack-${i}`}><h3>{a.name || 'Attack'}{a.damage!==undefined?` · ${a.damage}`:''}</h3>{a.cost?.length?<p>Cost: {a.cost.join(' / ')}</p>:null}<p>{a.effect}</p></section>)}
     {card.effect && <p className="rule-text">{card.effect}</p>}
     {card.rules?.map((rule,i)=><p className="rule-text" key={i}>{rule}</p>)}
     {!card.effect && !card.rules?.length && !card.attacks?.length && !card.abilities?.length && <p>No rules text supplied for this printing.</p>}
     {card.description && <p>{card.description}</p>}
     <dl>{card.weaknesses?.length?<><dt>Weakness</dt><dd>{card.weaknesses.map(v=>`${v.type} ${v.value ?? ''}`).join(', ')}</dd></>:null}
      {card.resistances?.length?<><dt>Resistance</dt><dd>{card.resistances.map(v=>`${v.type} ${v.value ?? ''}`).join(', ')}</dd></>:null}
      {card.retreat!==undefined && <><dt>Retreat cost</dt><dd>{card.retreat}</dd></>}
     </dl>
     <h2>Source legality</h2><p>{Object.entries(card.legal || {}).map(([format,legal])=>`${format}: ${legal?'legal':'not legal'}`).join(' · ') || 'Not supplied'}</p>
     <p className="source-note">Source: {data.source}<br/>Checked: {data.checked_at}<br/>Fetched: {data.fetched_at}<br/>Legality reflects dated source flags; a missing format is unknown.</p>
    </section></div>
   {card.ownership && variationsOpen && <section id="detail-variations" className="variations-section" aria-label="Card variations">
    <Variations key={printingId} id={printingId} revision={revision} onChange={changed}/></section>}
   <CompetitiveDashboard key={printingId} id={printingId}/>
  </>}
 </main>
}
