import { useState } from 'react'
import { changeQuantity, type Ownership } from './api'

export function QuantityControls({id,ownership,total=false,onChange}:{id:string;ownership:Ownership;total?:boolean;onChange:(id:string,value:Ownership)=>void}) {
 const [busy,setBusy]=useState(false),[error,setError]=useState('')
 async function change(delta:number) {
  setBusy(true);setError('')
  try {onChange(id,await changeQuantity(id,ownership.variant,delta))}
  catch(reason){setError(reason instanceof Error?reason.message:'Unable to save quantity.')}
  finally{setBusy(false)}
 }
 return <div className="ownership-controls">
  <div className="quantity-row" aria-label={`Ownership ${id} ${ownership.variant}`}>
   <button aria-label={`Remove one ${id} ${ownership.variant}`} disabled={busy||ownership.quantity===0} onClick={()=>change(-1)}>−</button>
   <output aria-live="polite" aria-label={total?'Total owned':'Exact variation owned'}>{total?ownership.library_total:ownership.quantity}</output>
   <button aria-label={`Add one ${id} ${ownership.variant}`} disabled={busy||ownership.quantity>=9999} onClick={()=>change(1)}>+</button>
  </div>
  <small>{total?'Total across variations · ':''}{ownership.variant} · this variation: {ownership.quantity}</small>
  {error && <p role="alert">{error}</p>}
 </div>
}
