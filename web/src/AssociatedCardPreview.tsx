import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

export const CARD_PREVIEW_WIDTH=350
export const CARD_PREVIEW_DELAY=500

// Reading artwork only. This component never requests competitive statistics.
export function useCardPreview(name:string,imageUrl?:string|null,printedText?:string) {
 const [position,setPosition]=useState<{left:number;top:number;width:number}|null>(null)
 const [failed,setFailed]=useState(false)
 const timer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined)
 const tooltipId=useId()
 const close=()=>{clearTimeout(timer.current);setPosition(null)}
 useEffect(()=>()=>clearTimeout(timer.current),[])
 useEffect(()=>{setFailed(false)},[imageUrl])
 useEffect(()=>{setPosition(null)},[name])
 useEffect(()=>{
  if(!position)return
  const dismiss=(event:Event)=>{if(event.type==='keydown'&&(event as KeyboardEvent).key!=='Escape')return;close()}
  window.addEventListener('scroll',dismiss,true);window.addEventListener('resize',dismiss);window.addEventListener('keydown',dismiss)
  return()=>{window.removeEventListener('scroll',dismiss,true);window.removeEventListener('resize',dismiss);window.removeEventListener('keydown',dismiss)}
 },[position])
 const show=(element:HTMLElement)=>{
  clearTimeout(timer.current)
  const rect=element.getBoundingClientRect(),width=Math.min(CARD_PREVIEW_WIDTH,window.innerWidth-24),height=Math.min(width*1.4+36,window.innerHeight-24)
  const left=rect.right+12+width<=window.innerWidth?rect.right+12:Math.max(12,rect.left-width-12)
  setPosition({left,top:Math.max(12,Math.min(rect.top,window.innerHeight-height-12)),width})
 }
 const enter=(element:HTMLElement)=>{clearTimeout(timer.current);timer.current=setTimeout(()=>show(element),CARD_PREVIEW_DELAY)}
 const leave=()=>{clearTimeout(timer.current);timer.current=setTimeout(close,150)}
 const preview=<>
 {position&&createPortal(<div id={tooltipId} role="tooltip" aria-label={`${name} ${printedText?'printed text':'card preview'}`} className="associated-card-preview" style={position} onPointerEnter={()=>clearTimeout(timer.current)} onPointerLeave={leave}>
  <strong>{name}</strong>{printedText?<p>{printedText}</p>:imageUrl&&!failed?<img src={imageUrl} alt={`${name} card artwork`} onError={()=>setFailed(true)}/>:<p>Image unavailable</p>}
 </div>,document.body)}</>
 return {enter,leave,show,preview,tooltipId,open:!!position}
}

export function AssociatedCardPreview({name,imageUrl,onClick,printedText}:{name:string;imageUrl?:string|null;onClick?:()=>void;printedText?:string}) {
 const hover=useCardPreview(name,imageUrl,printedText)
 return <><button className="associated-card-name" onClick={onClick} aria-describedby={hover.open?hover.tooltipId:undefined} onPointerEnter={e=>hover.enter(e.currentTarget)} onPointerLeave={hover.leave} onFocus={e=>hover.show(e.currentTarget)} onBlur={hover.leave}>{name}</button>{hover.preview}</>
}
