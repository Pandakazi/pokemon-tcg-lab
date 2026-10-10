export type DeckRow={category?:string;canonical_name:string;printing_id:string;quantity:number}
const order=['Pokemon','Trainer','Energy']
export function orderedDeck<T extends DeckRow>(rows:T[]):T[] {
 return [...rows].sort((a,b)=>(order.includes(a.category||'')?order.indexOf(a.category!):3)-(order.includes(b.category||'')?order.indexOf(b.category!):3))
}
export async function deckListText(rows:DeckRow[]):Promise<{text:string;warnings:string[]}> {
 const response=await fetch('/api/v1/decks/export-ptcgl',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({cards:orderedDeck(rows).map(r=>({printing_id:r.printing_id,quantity:r.quantity}))})})
 const result=await response.json()
 if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'PTCGL export is unavailable. Nothing was copied.')
 if(typeof result.text!=='string'||!Array.isArray(result.warnings))throw new Error('PTCGL export is unavailable. Nothing was copied.')
 return result
}
