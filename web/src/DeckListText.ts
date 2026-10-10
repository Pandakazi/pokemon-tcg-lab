export type DeckRow={category?:string;canonical_name:string;printing_id:string;quantity:number}
const order=['Pokemon','Trainer','Energy']
export function orderedDeck<T extends DeckRow>(rows:T[]):T[] {
 return [...rows].sort((a,b)=>(order.includes(a.category||'')?order.indexOf(a.category!):3)-(order.includes(b.category||'')?order.indexOf(b.category!):3))
}
// No PTCGL importer/exporter exists in this web app. Preserve exact identifiers
// in a clean plain-text list rather than pretending TCGdex IDs are PTCGL set codes.
export function deckListText(rows:DeckRow[]) {
 const sorted=orderedDeck(rows),lines:string[]=[]
 for(const category of [...order,undefined]){
  const group=sorted.filter(r=>category===undefined?!order.includes(r.category||''):r.category===category)
  if(!group.length)continue
  lines.push(`${category==='Pokemon'?'Pokémon':category||'Cards'}: ${group.reduce((sum,r)=>sum+r.quantity,0)}`)
  lines.push(...group.map(r=>`${r.quantity} ${r.canonical_name} (${r.printing_id})`),'')
 }
 lines.push(`Total Cards: ${rows.reduce((sum,r)=>sum+r.quantity,0)}`)
 return lines.join('\n')
}
