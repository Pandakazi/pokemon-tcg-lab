import {useEffect,useState} from 'react'

export type Appearance='system'|'light'|'dark'
export const APPEARANCE_KEY='pokelab.appearance'
export function savedAppearance():Appearance {
 try {const value=localStorage.getItem(APPEARANCE_KEY);if(value==='light'||value==='dark')return value} catch {/* Storage may be disabled. */}
 return 'system'
}
export function useAppearance() {
 const [appearance,setAppearance]=useState<Appearance>(savedAppearance)
 const [persisted,setPersisted]=useState(true)
 useEffect(()=>{
  const media=window.matchMedia('(prefers-color-scheme: dark)')
  const apply=()=>{document.documentElement.dataset.theme=appearance==='system'?(media.matches?'dark':'light'):appearance}
  apply();media.addEventListener?.('change',apply)
  return()=>media.removeEventListener?.('change',apply)
 },[appearance])
 useEffect(()=>{
  const changed=(event:StorageEvent)=>{if(event.key===APPEARANCE_KEY||event.key===null)setAppearance(savedAppearance())}
  window.addEventListener('storage',changed);return()=>window.removeEventListener('storage',changed)
 },[])
 const choose=(value:Appearance)=>{
  setAppearance(value)
  try{localStorage.setItem(APPEARANCE_KEY,value);setPersisted(true)}catch{setPersisted(false)}
 }
 return {appearance,choose,persisted}
}
