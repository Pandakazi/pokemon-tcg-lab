import { act, fireEvent, render, screen, cleanup } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { CardTile } from './CardTile'
import { CardDetail } from './CardDetail'
import { CompetitiveProvider, CompetitiveDashboard, UsageTrend, type Research } from './Competitive'
import type { Card } from './api'

const card:Card={id:'test-1',name:'Test Card',category:'Trainer',localId:1,set:{id:'test'},legal:{standard:true},legality_provenance:{source:'TCGdex',checked_at:'2026-09-24'},image_url:'/image.webp'}
const data:Research={schema_version:1,source:'limitless-main',window:'30',status:'observed',format_available:true,format_start:'2026-01-01',period_start:'2026-08-26',period_end:'2026-09-24',usage_percent:20,average_copies:3,included_decks:20,sample_size:100,tournament_count:3,published_decklists:105,excluded_unmapped:5,results_without_lists:10,last_updated:'2026-09-24',source_error:null,
 top_archetypes:Array.from({length:6},(_,i)=>({id:String(i),name:`Archetype ${i}`,decks:3,eligible_decks:99,share_percent:15,prevalence_percent:null,status:'insufficient_sample'})),archetypes:[],copy_distribution:[{copies:'1x',decks:2,percent:10}],associated_cards:[],association_status:'insufficient_sample',parser_version:'main-html-v1',provenance:[],
 trend:(['7','30','90','format'] as const).map(window=>({window,available:true,points:[{date:'2026-09-20',usage_percent:20,sample_size:100,included_decks:20},{date:'2026-09-23',usage_percent:25,sample_size:120,included_decks:30}]}))}
const advance=async(ms:number)=>{await act(async()=>{vi.advanceTimersByTime(ms)})}
function mount(list=false,competitive=true){return render(<MemoryRouter><CompetitiveProvider><CardTile card={card} list={list} competitive={competitive}/></CompetitiveProvider></MemoryRouter>)}
beforeEach(()=>{HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','')};HTMLDialogElement.prototype.close=function(){this.removeAttribute('open')};vi.useFakeTimers();vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>data}))})
afterEach(()=>{cleanup();vi.useRealTimers();vi.unstubAllGlobals()})

test.each([false,true])('Library hover waits exactly 1000ms, top five only; list=%s',async list=>{
 const view=mount(list),tile=view.container.querySelector('article')!
 fireEvent.pointerEnter(tile);await advance(999)
 expect(screen.queryByRole('dialog')).toBeNull();expect(fetch).not.toHaveBeenCalled()
 await advance(1)
 expect(screen.getByRole('dialog')).toBeInTheDocument()
 expect(screen.getAllByRole('listitem')).toHaveLength(5)
 expect(fetch).toHaveBeenCalledWith(expect.stringContaining('window=30&source=limitless-main&trend=false'),expect.anything())
 expect(screen.queryByText('Archetype 5')).toBeNull()
})
test('early leave cancels and crossing to popup preserves it until grace expires',async()=>{
 const view=mount(),tile=view.container.querySelector('article')!
 fireEvent.pointerEnter(tile);await advance(800);fireEvent.pointerLeave(tile);await advance(1000)
 expect(fetch).not.toHaveBeenCalled()
 fireEvent.pointerEnter(tile);await advance(1000)
 fireEvent.pointerLeave(tile);await advance(100);fireEvent.pointerEnter(screen.getByRole('dialog'));await advance(300)
 expect(screen.getByRole('dialog')).toBeInTheDocument()
 fireEvent.scroll(screen.getByRole('dialog'));expect(screen.getByRole('dialog')).toBeInTheDocument()
 fireEvent.pointerLeave(screen.getByRole('dialog'));await advance(179);expect(screen.getByRole('dialog')).toBeInTheDocument()
 await advance(1);expect(screen.queryByRole('dialog')).toBeNull()
})
test('non-Library tiles never request competitive hover',async()=>{
 const view=mount(false,false);fireEvent.pointerEnter(view.container.querySelector('article')!);await advance(2000)
 expect(fetch).not.toHaveBeenCalled();expect(screen.queryByRole('dialog')).toBeNull()
})
test('dashboard is continuous, threshold state and all trend series persist across window switch',async()=>{
 vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>({...data,archetypes:data.top_archetypes})} as Response)
 const view=render(<CompetitiveProvider><CompetitiveDashboard id="test-1"/></CompetitiveProvider>);await advance(0)
 expect(screen.getAllByText('Insufficient sample — 99 decklists')).toHaveLength(6)
 expect(view.container.querySelectorAll('[data-series]')).toHaveLength(4)
 expect(screen.queryByRole('tab')).toBeNull()
 fireEvent.click(screen.getAllByRole('button',{name:'7D'})[0]);await advance(0)
 expect(fetch).toHaveBeenLastCalledWith(expect.stringContaining('window=7'),expect.anything())
 expect(view.container.querySelectorAll('[data-series]')).toHaveLength(4)
 expect(screen.getByRole('heading',{name:'Evidence / Dataset'})).toBeInTheDocument()
})
test('unavailable Format is disabled and observed zero is displayed',async()=>{
 vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>({...data,format_available:false,usage_percent:0})} as Response)
 render(<CompetitiveProvider><CompetitiveDashboard id="test-1"/></CompetitiveProvider>);await advance(0)
 expect(screen.getAllByRole('button',{name:'Format'})[0]).toBeDisabled()
 expect(screen.getByText('0%',{selector:'dd'})).toBeInTheDocument()
})
test('trend legend toggles and points expose exact percent and denominator',()=>{
 const view=render(<UsageTrend series={data.trend}/>);expect(view.container.querySelectorAll('[data-series]')).toHaveLength(4)
 const point=screen.getByLabelText('7D 2026-09-20: 20% of 100 eligible decklists')
 fireEvent.focus(point);expect(screen.getByText('7D: 20% · 100 eligible decklists')).toBeInTheDocument()
 fireEvent.click(screen.getByRole('button',{name:'7D'}));expect(view.container.querySelectorAll('[data-series]')).toHaveLength(3)
})
test('Card Detail artwork has no competitive hover and still enlarges on click',async()=>{
 vi.mocked(fetch).mockImplementation(async input=>({ok:true,json:async()=>String(input).includes('/competitive/')?data:{card,source:'TCGdex',checked_at:'today',fetched_at:'today'}} as Response))
 const view=render(<MemoryRouter initialEntries={['/cards/test-1']}><Routes><Route path="/cards/:printingId" element={<CardDetail/>}/></Routes></MemoryRouter>);await advance(0)
 const art=view.container.querySelector('.detail-art')!;fireEvent.pointerEnter(art);await advance(1500)
 expect(screen.queryByRole('dialog')).toBeNull();expect(screen.getByText('Click to enlarge')).toBeInTheDocument()
 fireEvent.click(screen.getByRole('button',{name:/enlarge/i}));expect(screen.getByRole('dialog')).toBeInTheDocument()
 expect(view.container.querySelector('.competitive-popup')).toBeNull()
})
