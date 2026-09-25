import { useState, type ImgHTMLAttributes } from 'react'
import { Link, useLocation } from 'react-router'
import { classification, type Card, type Ownership } from './api'
import { QuantityControls } from './QuantityControls'
import { Modal } from './MagnifiedArt'
import { Variations } from './Variations'
import { useCompetitiveHover, CompetitivePopup } from './Competitive'
import { useBuilder, detailPath, ReadOnlyOwnership, DeckControls } from './DeckBuilder'
type ArtProps={card:Card;eager?:boolean;artworkEvents?:Pick<ImgHTMLAttributes<HTMLImageElement>,'onPointerEnter'|'onPointerLeave'>}
export function CardImage(props:ArtProps) {
 return <ResolvedCardImage key={`${props.card.id}:${props.card.image_url}`} {...props}/>
}
function ResolvedCardImage({card,eager=false,artworkEvents}:ArtProps) {
 const [failed,setFailed]=useState(0)
 const fallback=eager&&card.image_url?.endsWith('/high.webp')?card.image_url.replace(/\/high\.webp$/,'/low.webp'):null
 const source=failed===0?card.image_url:failed===1?fallback:null
 return <div className="card-art">{source
   ? <img {...artworkEvents} src={source} alt={`${card.name} — ${card.id}`} loading={eager?'eager':'lazy'} onError={()=>setFailed(n=>n+1)}/>
   : <div className="image-fallback" role="img" aria-label={`${card.name}: image unavailable`}><strong>{card.name}</strong><span>Image unavailable</span><small>{card.id}</small></div>}</div>
}
export function CardTile({card,list=false,exact=false,competitive=false,onChange,onPreference}: {card:Card;list?:boolean;exact?:boolean;competitive?:boolean;onChange?:(id:string,o:Ownership)=>void;onPreference?:()=>void}) {
 const location=useLocation()
 const builder=useBuilder()
 const [choose,setChoose]=useState(false)
 const hover=useCompetitiveHover(competitive&&!choose)
 return <article className={list?'card-row':'card-tile'} data-printing-id={card.id}>
  <Link className="card-link" to={`${detailPath(card.id,!!builder)}${card.ownership?`?variant=${encodeURIComponent(card.ownership.variant)}`:''}`} state={{library:location.pathname+location.search}} aria-label={`View ${card.name}, ${card.id}`}>
   <CardImage card={card} artworkEvents={{onPointerEnter:e=>hover.enter(e.currentTarget),onPointerLeave:hover.leave}}/>
   <strong title={card.name}>{card.name}</strong>
   <div className="printing">{card.set.name || card.set.id} · {card.localId}</div>
   <code>{card.id}</code><div className="card-details">{classification(card)}</div>
   <small title={`TCGdex Standard flag checked ${card.legality_provenance.checked_at}`}>{card.legal?.standard?'Standard':'Not source-marked Standard'} · {card.regulationMark || 'No regulation mark supplied'}</small>
  </Link>
  {builder?<><ReadOnlyOwnership card={card}/><DeckControls card={card}/></>:card.ownership && <QuantityControls id={card.id} ownership={card.ownership} total={!exact} onChange={(id,o)=>onChange?.(id,o)}/>}
  {card.ownership && !exact && !builder && <button className="choose-artwork" onClick={()=>setChoose(true)}>Choose artwork / finish</button>}
  {choose && <Modal title={`Library artwork — ${card.name}`} onClose={()=>setChoose(false)}><Variations id={card.id} library onSelected={()=>{setChoose(false);onPreference?.()}}/></Modal>}
  {competitive&&<CompetitivePopup id={card.id} name={card.name} deckIdentity={card.deck_identity} hover={hover}/>}
 </article>
}
