import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

// Reading artwork only. This component never requests competitive statistics.
export function AssociatedCardPreview({name,imageUrl}:{name:string;imageUrl?:string|null}) {
 const [position,setPosition]=useState<{left:number;top:number;width:number}|null>(null)
 const [failed,setFailed]=useState(false)
 const timer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined)
 const tooltipId=useId()
 const close=()=>{clearTimeout(timer.current);setPosition(null)}
 useEffect(()=>()=>clearTimeout(timer.current),[])
 useEffect(()=>{setFailed(false);setPosition(null)},[imageUrl])
 useEffect(()=>{
  if(!position)return
  const dismiss=(event:Event)=>{if(event.type==='keydown'&&(event as KeyboardEvent).key!=='Escape')return;close()}
  window.addEventListener('scroll',dismiss,true);window.addEventListener('resize',dismiss);window.addEventListener('keydown',dismiss)
  return()=>{window.removeEventListener('scroll',dismiss,true);window.removeEventListener('resize',dismiss);window.removeEventListener('keydown',dismiss)}
 },[position])
 const show=(element:HTMLElement)=>{
  clearTimeout(timer.current)
  const rect=element.getBoundingClientRect(),width=Math.min(350,window.innerWidth-24),height=Math.min(width*1.4+36,window.innerHeight-24)
  const left=rect.right+12+width<=window.innerWidth?rect.right+12:Math.max(12,rect.left-width-12)
  setPosition({left,top:Math.max(12,Math.min(rect.top,window.innerHeight-height-12)),width})
 }
 const leave=()=>{timer.current=setTimeout(close,150)}
 return <><button className="associated-card-name" aria-describedby={position?tooltipId:undefined} onPointerEnter={e=>show(e.currentTarget)} onPointerLeave={leave} onFocus={e=>show(e.currentTarget)} onBlur={leave}>{name}</button>
 {position&&createPortal(<div id={tooltipId} role="tooltip" aria-label={`${name} card preview`} className="associated-card-preview" style={position} onPointerEnter={()=>clearTimeout(timer.current)} onPointerLeave={leave}>
  <strong>{name}</strong>{imageUrl&&!failed?<img src={imageUrl} alt={`${name} card artwork`} onError={()=>setFailed(true)}/>:<p>Image unavailable</p>}
 </div>,document.body)}</>
}
