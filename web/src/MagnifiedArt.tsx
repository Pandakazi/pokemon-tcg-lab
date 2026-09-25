import { useEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { CardImage } from './CardTile'
import type { Card } from './api'
import { FinishImage } from './FinishImage'

export function Modal({title,onClose,children}:{title:string;onClose:()=>void;children:ReactNode}) {
 const dialog=useRef<HTMLDialogElement>(null)
 useEffect(()=>{dialog.current?.showModal();return ()=>dialog.current?.close()},[])
 return createPortal(<dialog ref={dialog} className="card-dialog" aria-label={title} onCancel={onClose}>
  <button className="dialog-close" onClick={onClose} aria-label={`Close ${title}`}>Close</button>
  <h2>{title}</h2>{children}
 </dialog>,document.body)
}

// Used exclusively on Card Detail; Library hover remains reserved for analytics.
export function MagnifiedArt({card,children}:{card:Card;children?:ReactNode}) {
 const [open,setOpen]=useState(false)
 const image=card.image_url?.replace('/low.webp','/high.webp')
 return <div className="magnifiable artwork-frame">
  <div className="embedded-artwork">{children || <button className="artwork-trigger" disabled={!image} onClick={()=>setOpen(true)} aria-label={`Enlarge ${card.name} ${card.id}`}><CardImage card={card} eager/></button>}</div>
  {!children && <p className="artwork-hint">Click to enlarge</p>}
  {open && <Modal title={`Artwork ${card.id}`} onClose={()=>setOpen(false)}><FinishImage finish={card.ownership?.variant} fullArt={/illustration rare/i.test(card.rarity||'')} className="enlarged-art" src={image!} alt={`${card.name} — ${card.id}`}/></Modal>}
 </div>
}
