import { beforeAll, expect, test, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'
import type { Card, Ownership } from './api'

beforeAll(()=>{
 HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','')}
 HTMLDialogElement.prototype.close=function(){this.removeAttribute('open')}
})
const ownership:Ownership={functional_id:'f1',library_id:'l1',variant:'normal',quantity:2,functional_total:4,library_total:4}
const first:Card={id:'sv01-1',name:'Collection test card',category:'Pokemon',localId:'1',set:{id:'sv01',name:'Test Set'},legal:{standard:true},image_url:'https://assets.tcgdex.net/en/sv/sv01/1/low.webp',legality_provenance:{source:'TCGdex',checked_at:'2026-09-24'},ownership}
const other:Card={...first,id:'sv02-2',localId:'2',ownership:{...ownership,variant:'reverse',quantity:2}}
const page=(cards:Card[])=>({cards,page:1,page_size:24,total:cards.length,next_page:null,sync:{status:'complete'}})
const ok=(data:unknown)=>({ok:true,json:async()=>data})

test('Gallery controls show rollup but mutate only the displayed exact finish',async()=>{
 let current=first
 const fetch=vi.fn(async(url:string,options?:RequestInit)=>{
  if(options?.method==='PUT') {expect(url).toBe('/api/v1/collection/sv01-1');expect(JSON.parse(options.body as string)).toEqual({variant:'normal',delta:1});current={...first,ownership:{...ownership,quantity:3,functional_total:5,library_total:5}};return ok(current.ownership)}
  return ok(page([current]))
 })
 vi.stubGlobal('fetch',fetch);render(<App/>);await screen.findByText('sv01-1')
 expect(screen.getByLabelText('Total owned')).toHaveTextContent('4')
 fireEvent.click(screen.getByRole('button',{name:'Add one sv01-1 normal'}))
 await waitFor(()=>expect(screen.getByLabelText('Total owned')).toHaveTextContent('5'))
 expect(screen.getByText(/this variation: 3/)).toBeInTheDocument()
})

test('Gallery minus cannot decrement another variation and failed writes do not change totals',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(_url:string,options?:RequestInit)=>options?.method==='PUT'?{ok:false,status:503}:ok(page([{...first,ownership:{...ownership,quantity:0}}]))))
 render(<App/>);await screen.findByText('sv01-1')
 expect(screen.getByRole('button',{name:'Remove one sv01-1 normal'})).toBeDisabled()
 fireEvent.click(screen.getByRole('button',{name:'Add one sv01-1 normal'}))
 expect(await screen.findByRole('alert')).toHaveTextContent('Unable to save')
 expect(screen.getByLabelText('Total owned')).toHaveTextContent('4')
})

test('Owned scope preserves current filters in its shareable query',async()=>{
 window.history.replaceState({},'','/?pokemon_types=Psychic&pokemon_types=Dragon&stages=Basic&ability=Yes&page=2')
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>ok({...page([first]),page:Number(new URL(url,'http://localhost').searchParams.get('page')||1)})))
 render(<App/>);await screen.findByText('sv01-1')
 fireEvent.click(screen.getByRole('button',{name:'Owned'}))
 expect(window.location.search).toContain('ownership=owned')
 expect(window.location.search).toContain('pokemon_types=Psychic&pokemon_types=Dragon&stages=Basic&ability=Yes')
 expect(window.location.search).not.toContain('page=2')
})

test('Library artwork selection writes a preference without changing ownership',async()=>{
 let selected=first
 const fetch=vi.fn(async(url:string,options?:RequestInit)=>{
  if(options?.method==='PUT'){expect(url).toBe('/api/v1/library/sv01-1/preference');expect(JSON.parse(options.body as string)).toEqual({printing_id:'sv02-2',variant:'reverse'});selected=other;return ok({printing_id:'sv02-2',variant:'reverse'})}
  return ok(url.includes('/variations')?page([first,other]):page([selected]))
 })
 vi.stubGlobal('fetch',fetch);render(<App/>);await screen.findByText('sv01-1')
 fireEvent.click(screen.getByRole('button',{name:'Choose artwork / finish'}))
 fireEvent.click(await screen.findByRole('button',{name:'Use sv02-2 reverse in Library'}))
 await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
 expect(await screen.findByRole('button',{name:'Add one sv02-2 reverse'})).toBeInTheDocument()
})

test('Detail variation inspection preserves preference and exact quantities; magnification has keyboard/touch fallback',async()=>{
 window.history.replaceState({},'','/cards/sv01-1?variant=normal')
 const fetch=vi.fn(async(url:string)=>ok(url.includes('/variations')?page([first,other]):{card:url.includes('sv02-2')?other:first,source:'TCGdex SQLite',checked_at:'today',fetched_at:'today',live:false,game:'tcg'}))
 vi.stubGlobal('fetch',fetch);render(<App/>);await screen.findByRole('heading',{name:first.name})
 expect(screen.getByLabelText('Exact variation owned')).toHaveTextContent('2')
 fireEvent.click(screen.getByRole('button',{name:'Enlarge Collection test card sv01-1'}))
 expect(screen.getByRole('dialog',{name:'Artwork sv01-1'})).toBeInTheDocument()
 fireEvent.click(screen.getByRole('button',{name:'Close Artwork sv01-1'}))
 fireEvent.click(screen.getByRole('button',{name:'Variations'}))
 fireEvent.click(await screen.findByRole('link',{name:'Inspect sv02-2 reverse'}))
 await waitFor(()=>expect(window.location.pathname).toBe('/cards/sv02-2'))
 expect(window.location.search).toBe('?variant=reverse')
 expect(fetch.mock.calls.every(args=>!args[0].includes('/preference'))).toBe(true)
})

test('Collection workspace exposes exact owned variations and totals',async()=>{
 window.history.replaceState({},'','/collection')
 vi.stubGlobal('fetch',vi.fn(async()=>ok(page([first,other]))))
 render(<App/>);expect(await screen.findByText('sv02-2')).toBeInTheDocument()
 expect(screen.getAllByLabelText('Exact variation owned')).toHaveLength(2)
 expect(screen.queryByRole('button',{name:'Choose artwork / finish'})).not.toBeInTheDocument()
 fireEvent.click(screen.getByRole('button',{name:'List'}))
 expect(document.querySelectorAll('.card-row')).toHaveLength(2)
})
