import {useEffect, useState} from 'react'

export function publishAgentStatus(status:unknown) {
 window.dispatchEvent(new CustomEvent('pokelab-agent-status',{detail:status}))
}
export function agentSettingsChanged() {
 window.dispatchEvent(new Event('pokelab-agent-settings-changed'))
}
export function useAgentSettingsRevision() {
 const [revision,setRevision]=useState(0)
 useEffect(()=>{
  const changed=()=>setRevision(value=>value+1)
  window.addEventListener('pokelab-agent-settings-changed',changed)
  return()=>window.removeEventListener('pokelab-agent-settings-changed',changed)
 },[])
 return revision
}
