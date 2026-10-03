import {useEffect,useRef,useState} from 'react'
import {AssociatedCardPreview} from './AssociatedCardPreview'
import {loadDetail} from './api'

export type ResearchCard={id:string;name:string;printing:string;printedText?:string}
function ResearchCardName({card,inspect}:{card:ResearchCard;inspect:(id:string)=>void}) {
 const [image,setImage]=useState<string|null>(null)
 const request=useRef<AbortController|null>(null)
 useEffect(()=>()=>request.current?.abort(),[])
 const preview=()=>{
  if(card.printedText)return
  if(request.current)return
  const controller=new AbortController();request.current=controller
  // Artwork lookup only, using the exact printing in the submitted evidence.
  // No competitive request, context mutation, or research submission.
  void loadDetail(card.printing,controller.signal).then(detail=>{
   if(!controller.signal.aborted)setImage(detail.card.image_url?.replace('/low.webp','/high.webp')||null)
  }).catch(()=>{/* Shared preview retains its accessible unavailable state. */})
 }
 return <span onPointerEnter={preview} onFocusCapture={preview}><AssociatedCardPreview name={card.name} imageUrl={image} printedText={card.printedText} onClick={()=>inspect(card.id)}/></span>
}

export function ResearchCardText({text,cards,inspect}:{text:string;cards:ResearchCard[];inspect:(id:string)=>void}) {
 const unique=cards.filter((c,i)=>cards.findIndex(other=>other.name===c.name)===i).sort((a,b)=>b.name.length-a.name.length)
 if(!unique.length)return <>{text}</>
 const escaped=unique.map(c=>c.name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'))
 const pattern=new RegExp(`(?<![\\p{L}\\p{N}])(${escaped.join('|')})(?![\\p{L}\\p{N}])`,'giu')
 const nodes=[];let end=0
 for(const match of text.matchAll(pattern)){
  nodes.push(text.slice(end,match.index))
  const card=unique.find(c=>c.name.toLocaleLowerCase()===match[0].toLocaleLowerCase())!
  nodes.push(<ResearchCardName key={`${match.index}-${card.id}`} card={card} inspect={inspect}/>);end=match.index!+match[0].length
 }
 nodes.push(text.slice(end));return <>{nodes}</>
}
