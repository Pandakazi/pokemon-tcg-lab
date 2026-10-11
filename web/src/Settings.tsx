import {useEffect,useRef,useState} from 'react'
import {useAppearance} from './Appearance'
import {agentSettingsChanged} from './AgentStatus'

type Provider='openai'|'gemini'
type AgentState={provider:Provider|null;connected:boolean;has_key:boolean;managed:boolean;storage:string;reason?:string|null}
type Progress={stage:string;message:string;settings?:AgentState}
const label=(provider:Provider)=>provider==='gemini'?'Gemini':'External provider'

export function SettingsControl() {
 const {appearance,choose,persisted}=useAppearance()
 const [menu,setMenu]=useState(false),[page,setPage]=useState<'agent'|'appearance'|null>(null)
 const [state,setState]=useState<AgentState|null>(null)
 const [key,setKey]=useState(''),[replace,setReplace]=useState(false),[pending,setPending]=useState(false)
 const [events,setEvents]=useState<Progress[]>([]),[error,setError]=useState(''),[loading,setLoading]=useState(false)
 const dialog=useRef<HTMLDialogElement>(null),gear=useRef<HTMLButtonElement>(null),menuRef=useRef<HTMLDivElement>(null)
 const flight=useRef(false),alive=useRef(true),controller=useRef<AbortController|null>(null)
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;controller.current?.abort()}},[])
 useEffect(()=>{
  const update=(event:Event)=>{
   const status=(event as CustomEvent).detail
   if(status&&typeof status.available==='boolean')setState(old=>({...old,provider:status.provider==='openai'||status.provider==='gemini'?status.provider:null,
    connected:status.available,has_key:old?.has_key??false,managed:old?.managed??false,storage:old?.storage??'external',reason:status.reason}))
  }
  window.addEventListener('pokelab-agent-status',update)
  return()=>window.removeEventListener('pokelab-agent-status',update)
 },[])
 useEffect(()=>{
  if(page&&!dialog.current?.open)dialog.current?.showModal()
  if(!page&&dialog.current?.open)dialog.current.close()
 },[page])
 useEffect(()=>{
  if(!menu)return
  const outside=(event:PointerEvent)=>{if(!menuRef.current?.contains(event.target as Node))setMenu(false)}
  document.addEventListener('pointerdown',outside)
  return()=>document.removeEventListener('pointerdown',outside)
 },[menu])
 const open=(value:'agent'|'appearance')=>{
  setMenu(false);setPage(value);setKey('');setReplace(false);setError('');setEvents([])
  if(value==='agent'){
   const abort=new AbortController();controller.current=abort;setLoading(true)
   fetch('/api/v1/settings/agent',{signal:abort.signal,cache:'no-store'}).then(async response=>{
    if(!response.ok)throw new Error();const result:AgentState=await response.json()
    if(typeof result.connected!=='boolean'||!['openai','gemini',null].includes(result.provider))throw new Error()
    if(alive.current&&!abort.signal.aborted){setState(result)}
   }).catch(()=>{if(alive.current&&!abort.signal.aborted)setError('Unable to load Agent settings. Close and try again.')})
    .finally(()=>{if(alive.current&&!abort.signal.aborted)setLoading(false)})
  }
 }
 const close=()=>{if(flight.current)return;controller.current?.abort();setPage(null);setKey('');setError('');gear.current?.focus()}
 const notify=(result:AgentState)=>{setState(result);setReplace(false);agentSettingsChanged()}
 const apply=async()=>{
  if(flight.current||!key.trim())return
  flight.current=true;setPending(true);setError('');setEvents([])
  const abort=new AbortController();controller.current=abort
  const timer=setTimeout(()=>abort.abort(),110000)
  const submitted=key;setKey('')
  try{
   const response=await fetch('/api/v1/settings/agent/test-apply',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({provider:'gemini',api_key:submitted}),signal:abort.signal})
   if(!response.ok||!response.body)throw new Error()
   const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',finished=false
   const consume=(line:string)=>{
    if(!line.trim())return
    const event:Progress=JSON.parse(line)
    if(!['validating','connecting','testing','saving','connected','failed'].includes(event.stage)||typeof event.message!=='string')throw new Error()
    if(alive.current){setEvents(old=>[...old,event]);if(event.stage==='connected'&&event.settings){notify(event.settings);finished=true}
     if(event.stage==='failed'){setError(event.message);finished=true}}
   }
   while(true){const chunk=await reader.read();if(chunk.done)break;buffer+=decoder.decode(chunk.value,{stream:true})
    let end;while((end=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,end));buffer=buffer.slice(end+1)}}
   buffer+=decoder.decode();consume(buffer)
   if(!finished)throw new Error()
  }catch{if(alive.current)setError('Connection test did not complete. Reload Agent settings to check the result before trying again.')}
  finally{clearTimeout(timer);flight.current=false;if(alive.current)setPending(false)}
 }
 const disconnect=async()=>{
  if(flight.current)return
  flight.current=true;setPending(true);setError('');setKey('');setEvents([])
  try{
   const response=await fetch('/api/v1/settings/agent/disconnect',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})
   const result=await response.json()
   if(!response.ok||!result.ok){if(alive.current)setError(result.message||'Unable to disconnect. Try again.');return}
   if(alive.current)notify(result.settings)
  }catch{if(alive.current)setError('Unable to disconnect. Check the API and try again.')}
  finally{flight.current=false;if(alive.current)setPending(false)}
 }
 const entering=replace||!state?.has_key||state?.provider!=='gemini'
 return <>
  <span className="agent-connection" aria-live="polite">Agent: {state?.connected?(state.provider?`${label(state.provider)} · Connected`:'Configured externally'):state?'Disconnected':'Checking…'}</span>
  <div className="settings-control" ref={menuRef} onKeyDown={event=>{if(event.key==='Escape'){setMenu(false);gear.current?.focus()}}}>
   <button ref={gear} className="settings-gear" aria-label="Settings" aria-expanded={menu} aria-haspopup="true" onClick={()=>setMenu(value=>!value)}>⚙</button>
   {menu&&<div className="settings-menu" aria-label="Settings options"><button autoFocus onClick={()=>open('agent')}>Agent Settings</button><button onClick={()=>open('appearance')}>Appearance</button></div>}
  </div>
  <dialog ref={dialog} className="settings-dialog" aria-labelledby="settings-title" onCancel={event=>{event.preventDefault();close()}} onClose={()=>{if(!flight.current){setPage(null);setKey('');gear.current?.focus()}}}>
   {page&&<>
   <h2 id="settings-title">{page==='appearance'?'Appearance':'Agent Settings'}</h2>
   {page==='appearance'?<>
    <fieldset><legend>Theme</legend>{(['system','light','dark'] as const).map(value=><label key={value}><input type="radio" name="appearance" checked={appearance===value} onChange={()=>choose(value)}/>{value[0].toUpperCase()+value.slice(1)}</label>)}</fieldset>
    <p>System follows your device’s appearance. Card artwork and finish effects keep their original colors.</p>
    {!persisted&&<p role="alert">Browser storage is unavailable. This choice will last for this session.</p>}
   </>:<>
    {loading&&<p>Loading Agent settings…</p>}
    <p>AI provider: Gemini</p>
    {state?.connected&&<p>{state.provider?label(state.provider):'External provider'} connected{state.storage==='session'?' for this session':''}.</p>}
    {entering?<label className="key-label" htmlFor="agent-api-key">Gemini API Key<input id="agent-api-key" type="password" autoComplete="off" spellCheck={false} maxLength={2048} value={key} disabled={pending||loading} onChange={event=>setKey(event.target.value)}/></label>:<p>Saved API key: ••••••••••••</p>}
    <p>Test &amp; Apply sends one small request to Gemini. API charges may apply. Windows saves your key encrypted for your account; other platforms keep it only for this session.</p>
    <div className="settings-actions">
     {entering?<button disabled={pending||loading||!key.trim()} onClick={()=>void apply()}>Test &amp; Apply</button>:<button disabled={pending||loading} onClick={()=>{setReplace(true);setKey('');setEvents([]);setError('')}}>Replace Key</button>}
     {(state?.connected||state?.has_key)&&<button disabled={pending||loading} onClick={()=>void disconnect()}>Disconnect</button>}
    </div>
    {!!events.length&&<div className="settings-progress" role="status" aria-live="polite"><progress aria-label="Connection progress" max={5} value={events.filter(event=>event.stage!=='failed').length}/><ol>{events.map((event,index)=><li key={index}>{event.message}</li>)}</ol></div>}
    {error&&<p role="alert">{error}</p>}
   </>}
   <button className="settings-done" disabled={pending} onClick={close}>Done</button>
   </>}
  </dialog>
 </>
}
