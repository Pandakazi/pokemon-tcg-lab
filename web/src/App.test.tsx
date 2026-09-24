import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { test, expect, vi } from 'vitest'
import App from './App'
import { CardTile } from './CardTile'
import type { Card } from './api'
const card: Card = {id:'sv02-097',name:'Test printing',category:'Pokemon',localId:'097',set:{id:'sv02',name:'Paldea Evolved'},legal:{standard:true},image_url:'https://assets.tcgdex.net/en/sv/sv02/097/low.webp',legality_provenance:{source:'TCGdex',checked_at:'2026-09-23'}}
const result = (page=1) => ({cards:[{...card,id:page===1?card.id:'sv02-098'}],page,page_size:24,total:25,next_page:page===1?2:null,sync:{status:'complete'}})
test('shows loading until the API returns', async () => {
 let resolve!: (v: unknown) => void
 vi.stubGlobal('fetch', vi.fn(() => new Promise(r => {resolve=r})))
 render(<App/>); expect(screen.getByRole('status')).toHaveTextContent('Loading cards')
 resolve({ok:true,json:async()=>result()})
 expect(await screen.findByText('Test printing')).toBeInTheDocument()
 expect(screen.getByText('sv02-097')).toBeInTheDocument()
 expect(screen.getByText('Paldea Evolved · 097')).toBeInTheDocument()
 expect(screen.getByRole('img')).toHaveAttribute('src',card.image_url)
})
test('renders database failure and retries', async () => {
 const fetch=vi.fn().mockResolvedValueOnce({ok:false,status:503}).mockResolvedValue({ok:true,json:async()=>result()})
 vi.stubGlobal('fetch',fetch); render(<App/>)
 expect(await screen.findByRole('alert')).toHaveTextContent('database is unavailable')
 fireEvent.click(screen.getByText('Retry'))
 expect(await screen.findByText('Test printing')).toBeInTheDocument()
})
test('network failure does not display fake cards', async () => {
 vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('Offline'))); render(<App/>)
 expect(await screen.findByRole('alert')).toHaveTextContent('Offline')
 expect(screen.queryByText('Dragapult ex')).not.toBeInTheDocument()
})
test('pagination requests and renders a different exact printing', async () => {
 const fetch=vi.fn().mockImplementation(async (url:string)=>({ok:true,json:async()=>result(url.includes('page=2')?2:1)}))
 vi.stubGlobal('fetch',fetch); render(<App/>); await screen.findByText('sv02-097')
 fireEvent.click(screen.getByText('Next')); await screen.findByText('sv02-098')
 expect(screen.getByText('Next')).toBeDisabled()
 fireEvent.click(screen.getByText('Previous')); await screen.findByText('sv02-097')
 expect(fetch).toHaveBeenCalledWith(expect.stringContaining('page=2'),expect.anything())
})
test('broken and missing images have meaningful fallbacks', async () => {
 const {rerender}=render(<CardTile card={card}/>); fireEvent.error(screen.getByRole('img'))
 expect(screen.getByRole('img')).toHaveAccessibleName('Test printing: image unavailable')
 rerender(<CardTile key="other" card={{...card,image_url:null}}/>)
 expect(screen.getByText('Image unavailable')).toBeInTheDocument()
})
test('malformed API response shows an error', async () => {
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({cards:'invalid'})}))
 render(<App/>); expect(await screen.findByRole('alert')).toHaveTextContent('unexpected response')
})
