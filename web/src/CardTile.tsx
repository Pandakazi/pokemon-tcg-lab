import { useState } from 'react'
import { Link, useLocation } from 'react-router'
import { classification, type Card } from './api'
export function CardImage({card, eager=false}: {card:Card; eager?:boolean}) {
 const [failed,setFailed]=useState(false)
 return <div className="card-art">{card.image_url && !failed
   ? <img src={card.image_url} alt={`${card.name} — ${card.id}`} loading={eager?'eager':'lazy'} onError={()=>setFailed(true)}/>
   : <div className="image-fallback" role="img" aria-label={`${card.name}: image unavailable`}><strong>{card.name}</strong><span>Image unavailable</span><small>{card.id}</small></div>}</div>
}
export function CardTile({card,list=false}: {card:Card;list?:boolean}) {
 const location=useLocation()
 return <article className={list?'card-row':'card-tile'} data-printing-id={card.id}>
  <Link className="card-link" to={`/cards/${encodeURIComponent(card.id)}`} state={{library:location.pathname+location.search}} aria-label={`View ${card.name}, ${card.id}`}>
   <CardImage card={card}/>
   <strong title={card.name}>{card.name}</strong>
   <div className="printing">{card.set.name || card.set.id} · {card.localId}</div>
   <code>{card.id}</code><div className="card-details">{classification(card)}</div>
   <small title={`TCGdex Standard flag checked ${card.legality_provenance.checked_at}`}>Standard · {card.regulationMark || 'No regulation mark supplied'}</small>
  </Link>
 </article>
}
