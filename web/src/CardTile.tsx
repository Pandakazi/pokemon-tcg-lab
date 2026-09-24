import { useState } from 'react'
import { Link, useLocation } from 'react-router'
import { classification, type Card, type Ownership } from './api'
import { QuantityControls } from './QuantityControls'
import { Modal } from './MagnifiedArt'
import { Variations } from './Variations'
export function CardImage({card, eager=false}: {card:Card; eager?:boolean}) {
 const [failed,setFailed]=useState(false)
 return <div className="card-art">{card.image_url && !failed
   ? <img src={card.image_url} alt={`${card.name} — ${card.id}`} loading={eager?'eager':'lazy'} onError={()=>setFailed(true)}/>
   : <div className="image-fallback" role="img" aria-label={`${card.name}: image unavailable`}><strong>{card.name}</strong><span>Image unavailable</span><small>{card.id}</small></div>}</div>
}
export function CardTile({card,list=false,exact=false,onChange,onPreference}: {card:Card;list?:boolean;exact?:boolean;onChange?:(id:string,o:Ownership)=>void;onPreference?:()=>void}) {
 const location=useLocation()
 const [choose,setChoose]=useState(false)
 return <article className={list?'card-row':'card-tile'} data-printing-id={card.id}>
  <Link className="card-link" to={`/cards/${encodeURIComponent(card.id)}${card.ownership?`?variant=${encodeURIComponent(card.ownership.variant)}`:''}`} state={{library:location.pathname+location.search}} aria-label={`View ${card.name}, ${card.id}`}>
   <CardImage card={card}/>
   <strong title={card.name}>{card.name}</strong>
   <div className="printing">{card.set.name || card.set.id} · {card.localId}</div>
   <code>{card.id}</code><div className="card-details">{classification(card)}</div>
   <small title={`TCGdex Standard flag checked ${card.legality_provenance.checked_at}`}>{card.legal?.standard?'Standard':'Not source-marked Standard'} · {card.regulationMark || 'No regulation mark supplied'}</small>
  </Link>
  {card.ownership && <QuantityControls id={card.id} ownership={card.ownership} total={!exact} onChange={(id,o)=>onChange?.(id,o)}/>}
  {card.ownership && !exact && <button className="choose-artwork" onClick={()=>setChoose(true)}>Choose artwork / finish</button>}
  {choose && <Modal title={`Library artwork — ${card.name}`} onClose={()=>setChoose(false)}><Variations id={card.id} library onSelected={()=>{setChoose(false);onPreference?.()}}/></Modal>}
 </article>
}
