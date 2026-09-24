export interface Card {
  id: string; name: string; category: 'Pokemon'; localId: string | number
  set: { id: string; name?: string }; hp?: number; types?: string[]; stage?: string
  rarity?: string; regulationMark?: string; legal: { standard: boolean }
  image_url?: string | null
  legality_provenance: { source: string; checked_at: string }
}
export interface CardPage {
  cards: Card[]; page: number; page_size: number; total: number; next_page: number | null
  sync: { status: string; finished_at?: string }
}
export async function loadCards(page: number, signal: AbortSignal): Promise<CardPage> {
  const response = await fetch(`/api/v1/cards?page=${page}&page_size=24&include_image=true`, { signal })
  if (!response.ok) throw new Error(response.status === 503
    ? 'The local card database is unavailable. Initialize or check the database, then retry.'
    : `The card API returned an error (${response.status}). Please retry.`)
  const data = await response.json()
  if (!Array.isArray(data.cards) || !Number.isInteger(data.total) || data.page !== page)
    throw new Error('The card API returned an unexpected response.')
  return data
}
