export type Category = 'Pokemon' | 'Trainer' | 'Energy'
export interface Card {
  id: string; name: string; category: Category; localId: string | number
  set: { id: string; name?: string; code?: string }; hp?: number; types?: string[]; stage?: string
  rarity?: string; regulationMark?: string; legal: Record<string, boolean>
  trainerType?: string; energyType?: string; suffix?: string
  image_url?: string | null
  legality_provenance: { source: string; checked_at: string }
}
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
export async function loadDetail(id: string, signal: AbortSignal): Promise<Detail> {
  const data = await read(`/api/v1/cards/${encodeURIComponent(id)}?include_image=true`,signal)
  if (!data.card || data.card.id !== id) throw new Error('The card API returned an unexpected printing.')
  return data
}
export function classification(card: Card) {
  return [card.category, card.stage, card.types?.join(' / '), card.trainerType,
    card.energyType === 'Normal' ? 'Basic Energy' : card.energyType === 'Special' ? 'Special Energy' : card.energyType,
    card.hp ? `${card.hp} HP` : null].filter(Boolean).join(' · ')
}
