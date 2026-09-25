import { useLayoutEffect, useRef, type ImgHTMLAttributes, type PointerEvent } from 'react'

type Props = ImgHTMLAttributes<HTMLImageElement> & { finish?: string; fullArt?: boolean }

// Presentation only: never infer a finish from rarity or mutate the selected printing.
export function FinishImage({finish,fullArt=false,onPointerEnter,onPointerLeave,onPointerMove,...image}:Props) {
 const surface=useRef<HTMLSpanElement>(null),art=useRef<HTMLImageElement>(null),foil=useRef<HTMLSpanElement>(null)
 const media=useRef<{fine:MediaQueryList;reduced:MediaQueryList}|null>(null)
 const treatment=finish==='holo'?'holo':finish==='reverse'?'reverse':undefined
 useLayoutEffect(()=>{
  if(!treatment||!art.current||!surface.current)return
  media.current={fine:window.matchMedia('(hover: hover) and (pointer: fine)'),reduced:window.matchMedia('(prefers-reduced-motion: reduce)')}
  const img=art.current,root=surface.current
  function fit(){
   if(!foil.current)return
   const bounds=img.getBoundingClientRect(),parent=root.getBoundingClientRect()
   Object.assign(foil.current.style,{left:`${bounds.left-parent.left}px`,top:`${bounds.top-parent.top}px`,width:`${bounds.width}px`,height:`${bounds.height}px`,visibility:img.complete&&img.naturalWidth?'visible':'hidden'})
  }
  const observer=new ResizeObserver(fit);observer.observe(img);observer.observe(root)
  img.addEventListener('load',fit);fit()
  return ()=>{observer.disconnect();img.removeEventListener('load',fit)}
 },[treatment,image.src])
 function move(event:PointerEvent<HTMLImageElement>){
  if(event.pointerType==='touch'||!media.current?.fine.matches||media.current.reduced.matches)return
  const bounds=event.currentTarget.getBoundingClientRect(),root=surface.current!
  root.style.setProperty('--foil-x',`${Math.max(0,Math.min(100,(event.clientX-bounds.left)/bounds.width*100))}%`)
  root.style.setProperty('--foil-y',`${Math.max(0,Math.min(100,(event.clientY-bounds.top)/bounds.height*100))}%`)
  root.dataset.lit='true'
 }
 if(!treatment)return <img {...image} onPointerEnter={onPointerEnter} onPointerLeave={onPointerLeave} onPointerMove={onPointerMove}/>
 // Stable phase per printing/finish; no timers or animation state in React.
 const phase=`${image.src?.replace(/\/(high|low)\.webp$/,'')}:${treatment}`.split('').reduce((hash,char)=>(hash*31+char.charCodeAt(0))>>>0,0)%1200/100
 return <span ref={surface} className="finish-surface" data-finish={treatment} data-full-art={fullArt||undefined}>
  <img {...image} ref={art} onPointerEnter={e=>{move(e);onPointerEnter?.(e)}} onPointerMove={e=>{move(e);onPointerMove?.(e)}} onPointerLeave={e=>{
   const root=surface.current!;delete root.dataset.lit;root.style.removeProperty('--foil-x');root.style.removeProperty('--foil-y');onPointerLeave?.(e)
  }}/>
  <span ref={foil} className="finish-light" aria-hidden="true"><span className="finish-shimmer" style={{animationDelay:`-${phase}s`}}/></span>
 </span>
}
