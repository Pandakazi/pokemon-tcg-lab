import { MemoryRouter } from 'react-router'
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
 await waitFor(()=>expect(resolve).toBeTypeOf('function'))
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
 const {rerender}=render(<MemoryRouter><CardTile card={card}/></MemoryRouter>); fireEvent.error(screen.getByRole('img'))
 expect(screen.getByRole('img')).toHaveAccessibleName('Test printing: image unavailable')
 rerender(<MemoryRouter><CardTile key="other" card={{...card,image_url:null}}/></MemoryRouter>)
 expect(screen.getByText('Image unavailable')).toBeInTheDocument()
})
test('malformed API response shows an error', async () => {
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({cards:'invalid'})}))
 render(<App/>); expect(await screen.findByRole('alert')).toHaveTextContent('unexpected response')
})


test('URL category, search, filters and page survive a view switch without refetch', async () => {
 window.history.replaceState({},'', '/?category=Pokemon&q=Test&pokemon_types=Psychic&pokemon_types=Dragon&stages=Basic&page=2')
 const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({...result(2),filter_options:[{parameter:'pokemon_types',label:'Pokémon type',values:['Psychic','Dragon']},{parameter:'stages',label:'Stage',values:['Basic']}]})})
 vi.stubGlobal('fetch',fetch); render(<App/>); await screen.findByText('sv02-098')
 const url=window.location.search,calls=fetch.mock.calls.length
 fireEvent.click(screen.getByRole('button',{name:'List'}))
 expect(document.querySelector('.card-row')).not.toBeNull()
 expect(screen.getByRole('textbox',{name:'Search cards'})).toHaveValue('Test')
 expect(screen.getByLabelText('Psychic')).toBeChecked();expect(screen.getByLabelText('Dragon')).toBeChecked()
 expect(window.location.search).toBe(url); expect(fetch).toHaveBeenCalledTimes(calls)
 fireEvent.click(screen.getByRole('button',{name:'Gallery'}))
 expect(document.querySelector('.card-tile')).not.toBeNull()
 expect(window.location.search).toBe(url)
})
test('category changes clear incompatible filters and reset pagination, keeping search',async()=>{
 window.history.replaceState({},'','/?q=Test&pokemon_types=Psychic&page=2')
 vi.stubGlobal('fetch',vi.fn().mockImplementation(async (url:string)=>({ok:true,json:async()=>result(url.includes('page=2')?2:1)})))
 render(<App/>);await screen.findByText('sv02-098')
 fireEvent.click(screen.getByRole('button',{name:'Trainers'}));await screen.findByText('sv02-097')
 expect(window.location.search).toContain('category=Trainer');expect(window.location.search).toContain('q=Test')
 expect(window.location.search).not.toContain('pokemon_types');expect(window.location.search).not.toContain('page=2')
})
test('filter selections send repeated values and combine families on the server',async()=>{
 const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({...result(),filter_options:[{parameter:'pokemon_types',label:'Pokémon type',values:['Psychic','Dragon']},{parameter:'stages',label:'Stage',values:['Basic']}]})})
 vi.stubGlobal('fetch',fetch);render(<App/>);await screen.findByText('sv02-097')
 fireEvent.click(screen.getByLabelText('Psychic'));fireEvent.click(screen.getByLabelText('Dragon'));fireEvent.click(screen.getByLabelText('Basic'))
 await waitFor(()=>expect(fetch).toHaveBeenLastCalledWith(expect.stringMatching(/pokemon_types=Psychic.*pokemon_types=Dragon.*stages=Basic/),expect.anything()))
})
test('direct detail URL renders exact structured metadata and no fabricated research',async()=>{
 window.history.replaceState({},'','/cards/sv02-097')
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({card:{...card,types:['Psychic','Dragon'],attacks:[{name:'Test Attack',cost:['Psychic'],damage:20,effect:'Real fixture text'}]},source:'TCGdex SQLite',checked_at:'2026-09-23',fetched_at:'2026-09-23',live:false,game:'tcg'})}))
 render(<App/>);expect(await screen.findByRole('heading',{name:'Test printing'})).toBeInTheDocument()
 expect(screen.getByText('Real fixture text')).toBeInTheDocument();expect(screen.getByText(/Psychic \/ Dragon/)).toBeInTheDocument()
 expect(screen.getByText('sv02-097')).toBeInTheDocument();expect(screen.queryByText('Market')).not.toBeInTheDocument()
})
test('missing detail printing displays not-found and library navigation',async()=>{
 window.history.replaceState({},'','/cards/unknown-1')
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:404}));render(<App/>)
 expect(await screen.findByRole('alert')).toHaveTextContent('exact printing was not found')
 expect(screen.getByRole('link',{name:'← Back to library'})).toHaveAttribute('href','/')
})
test('empty filtered result is explicit',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({...result(),cards:[],total:0,next_page:null})}))
 render(<App/>);expect(await screen.findByText('No cards match this query.')).toBeInTheDocument()
 expect(screen.getByRole('button',{name:'Next'})).toBeDisabled()
})

test('old card links disappear immediately when the query changes',async()=>{
 const fetch=vi.fn().mockResolvedValueOnce({ok:true,json:async()=>result()}).mockImplementation(()=>new Promise(()=>{}))
 vi.stubGlobal('fetch',fetch);render(<App/>);await screen.findByText('sv02-097')
 fireEvent.click(screen.getByRole('button',{name:'Next'}))
 expect(screen.queryByRole('link',{name:'View Test printing, sv02-097'})).not.toBeInTheDocument()
 expect(screen.getByRole('status')).toHaveTextContent('Loading cards')
})

test('detail does not invent missing source legality',async()=>{
 window.history.replaceState({},'','/cards/sv02-097')
 const {legal,...unknown}=card
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({card:unknown,source:'TCGdex SQLite',checked_at:'2026-09-23',fetched_at:'2026-09-23',live:false,game:'tcg'})}))
 render(<App/>);expect(await screen.findByText('Not supplied')).toBeInTheDocument()
})
