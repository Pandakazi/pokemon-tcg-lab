import {useEffect,useRef,useState} from 'react'

type SyncState={status:string;last_successful_at?:string|null;available_at?:string|null;retry_after_seconds?:number;failed?:boolean}
export function freshness(timestamp:string|null|undefined,now=Date.now()) {
 if(!timestamp)return 'not synced yet'
 const minutes=Math.max(0,Math.floor((now-Date.parse(timestamp))/60000))
 return minutes<1?'synced just now':minutes<60?`synced ${minutes}m ago`:minutes<1440?`synced ${Math.floor(minutes/60)}h ago`:`synced ${new Date(timestamp).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})}`
}
export function CompetitiveSync() {
 const [state,setState]=useState<SyncState|null>(null),[pending,setPending]=useState(false),[error,setError]=useState(''),[manualFailure,setManualFailure]=useState(false),[now,setNow]=useState(Date.now())
 const flight=useRef(false),alive=useRef(true)
 useEffect(()=>{alive.current=true;const controller=new AbortController()
  fetch('/api/v1/competitive/sync',{signal:controller.signal}).then(async r=>{if(!r.ok)throw new Error();const s=await r.json();if(!['ready','cooldown','running'].includes(s.status))throw new Error();return s}).then(s=>{if(alive.current)setState(s)}).catch(()=>{if(!controller.signal.aborted)setError('Competitive refresh status is unavailable. Reload to check again.')})
  // Display clock only: no scheduled fetches or automatic synchronization.
  const timer=setInterval(()=>setNow(Date.now()),60000)
  return()=>{alive.current=false;controller.abort();clearInterval(timer)}
 },[])
 const remaining=state?.available_at?Math.max(0,Math.ceil((Date.parse(state.available_at)-now)/60000)):0
 const sync=async()=>{
  if(flight.current||!state||remaining||state.status==='running')return
  flight.current=true;setPending(true);setError('');setManualFailure(false)
  try{const r=await fetch('/api/v1/competitive/sync',{method:'POST'}),s:SyncState=await r.json()
   if(!r.ok&&r.status!==409)throw new Error()
   if(alive.current){setState(s);setNow(Date.now())}
  }catch{if(alive.current){setManualFailure(true);setError('Competitive data couldn’t be refreshed. Your previous data is still available.')}}
  finally{flight.current=false;if(alive.current)setPending(false)}
 }
 return <div className="source-note competitive-sync" aria-label="Competitive data sync">
  <span title={state?.last_successful_at?new Date(state.last_successful_at).toLocaleString():undefined}>Competitive data · {state?freshness(state.last_successful_at,now):error?'status unavailable':'checking freshness…'}</span>{' '}
  <button disabled={!state||pending||state.status==='running'||remaining>0} onClick={()=>void sync()}>{pending||state?.status==='running'?'Syncing…':'Sync Competitive Data'}</button>
  {remaining>0&&<span> · Available again in {remaining}m</span>}
  {(error||state?.failed)&&<p role={manualFailure||state?.failed?'alert':undefined}>{error||'Competitive data couldn’t be refreshed. Your previous data is still available.'}</p>}
 </div>
}
