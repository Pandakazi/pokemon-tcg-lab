export type Category = 'Pokemon' | 'Trainer' | 'Energy'
export interface Card {
  deck_identity?: string
  id: string; name: string; category: Category; localId: string | number
  set: { id: string; name?: string; code?: string }; hp?: number; types?: string[]; stage?: string
  rarity?: string; regulationMark?: string; legal: Record<string, boolean>
  trainerType?: string; energyType?: string; suffix?: string
  image_url?: string | null
  legality_provenance: { source: string; checked_at: string }
  ownership?: Ownership
}
export interface Ownership {functional_id:string;library_id:string;variant:string;quantity:number;functional_total:number;library_total:number}
export interface VariationPage {cards:Card[];unassigned?:Card[];total:number;page:number;page_size:number;next_page:number|null}
export function finishLabel(variant:string) {return variant==='unspecified'?'Finish not recorded':variant}
export interface FilterOption { parameter: string; label: string; values: string[] }
export interface CardPage {
  cards: Card[]; page: number; page_size: number; total: number; next_page: number | null
  sync: { status: string; finished_at?: string }; filter_options?: FilterOption[]
}
export interface Detail {
  card: Card & {effect?: string; description?: string; rules?: string[]; evolveFrom?: string; illustrator?: string
    abilities?: {type?: string; name?: string; effect?: string}[]
    attacks?: {name?: string; cost?: string[]; damage?: string | number; effect?: string}[]
    weaknesses?: {type: string; value?: string | number}[]; resistances?: {type: string; value?: string | number}[]; retreat?: number}
  source: string; checked_at: string; fetched_at: string; live: boolean; game: string
}
async function read(url: string, signal: AbortSignal) {
  const response = await fetch(url, { signal })
  if(response.status===503) {
    let body;try{body=await response.json()}catch{/* Non-JSON gateway failure uses the generic message below. */}
    if(body?.detail?.code==='user_state_unavailable') throw new Error('Local collection storage is unavailable. Check the user-state database path and permissions, then retry.')
  }
  if (!response.ok) throw new Error(response.status === 503
    ? 'The local card database is unavailable. Initialize or check the database, then retry.'
    : response.status === 404 ? 'This exact printing was not found in the local database.'
    : response.status === 422 ? 'Invalid library query. Clear the filters or check the URL.'
    : `The card API returned an error (${response.status}). Please retry.`)
  return response.json()
}
export async function loadCards(params: URLSearchParams, signal: AbortSignal): Promise<CardPage> {
  const query = new URLSearchParams(params)
  if (!query.has('page')) query.set('page', '1')
  query.set('page_size','24'); query.set('include_image','true')
  const data = await read(`/api/v1/cards?${query}`, signal)
  if (!Array.isArray(data.cards) || !Number.isInteger(data.total) || data.page !== Number(query.get('page')))
    throw new Error('The card API returned an unexpected response.')
  return data
}
export async function loadDetail(id: string, signal: AbortSignal, variant?:string): Promise<Detail> {
  const data = await read(`/api/v1/cards/${encodeURIComponent(id)}?include_image=true${variant?`&variant=${encodeURIComponent(variant)}`:''}`,signal)
  if (!data.card || data.card.id !== id) throw new Error('The card API returned an unexpected printing.')
  return data
}
export async function loadVariations(id:string,scope:'functional'|'library',page:number,signal:AbortSignal):Promise<VariationPage> {
 return read(`/api/v1/cards/${encodeURIComponent(id)}/variations?scope=${scope}&page=${page}&page_size=24`,signal)
}
export async function loadCollection(params:URLSearchParams,signal:AbortSignal):Promise<VariationPage> {
 const query=new URLSearchParams(params);query.set('page_size','24')
 return read(`/api/v1/collection?${query}`,signal)
}
async function write(url:string,body:object) {
 const response=await fetch(url,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
 if(!response.ok) throw new Error(response.status===422?'That quantity or variation is not valid.':'Unable to save local changes. Please retry.')
 return response.json()
}
export async function changeQuantity(id:string,variant:string,delta:number):Promise<Ownership> {
 return write(`/api/v1/collection/${encodeURIComponent(id)}`,{variant,delta})
}
export async function savePreference(anchor:string,card:Card) {
 return write(`/api/v1/library/${encodeURIComponent(anchor)}/preference`,{printing_id:card.id,variant:card.ownership!.variant})
}
export function withOwnership<T extends Card>(card:T,id:string,owned:Ownership):T {
 const current=card.ownership
 if(!current)return card
 return {...card,ownership:{...current,
  quantity:card.id===id && current.variant===owned.variant?owned.quantity:current.quantity,
  functional_total:current.functional_id===owned.functional_id?owned.functional_total:current.functional_total,
  library_total:current.library_id===owned.library_id?owned.library_total:current.library_total}}
}
export function classification(card: Card) {
  return [card.category, card.stage, card.types?.join(' / '), card.trainerType,
    card.energyType === 'Normal' ? 'Basic Energy' : card.energyType === 'Special' ? 'Special Energy' : card.energyType,
    card.hp ? `${card.hp} HP` : null].filter(Boolean).join(' · ')
}
