import { act, fireEvent, render, screen, cleanup } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { CardTile } from './CardTile'
import { CardDetail } from './CardDetail'
import { CompetitiveProvider, CompetitiveDashboard, UsageTrend, type Research } from './Competitive'
import type { Card } from './api'

const card:Card={id:'test-1',name:'Test Card',category:'Trainer',localId:1,set:{id:'test'},legal:{standard:true},legality_provenance:{source:'TCGdex',checked_at:'2026-09-24'},image_url:'/image.webp'}
const data:Research={archetype_prevalence_min_decks:15,schema_version:1,source:'limitless-main',window:'30',status:'observed',format_available:true,format_start:'2026-01-01',period_start:'2026-08-26',period_end:'2026-09-24',usage_percent:20,average_copies:3,included_decks:20,sample_size:100,tournament_count:3,published_decklists:105,excluded_unmapped:5,results_without_lists:10,last_updated:'2026-09-24',source_error:null,
 top_archetypes:Array.from({length:6},(_,i)=>({id:String(i),name:`Archetype ${i}`,decks:3,eligible_decks:14,share_percent:15,prevalence_percent:null,status:'insufficient_sample'})),archetypes:[],copy_distribution:[{copies:'1x',decks:2,percent:10}],associated_cards:[],association_status:'insufficient_sample',parser_version:'main-html-v1',provenance:[],
 trend:(['7','30','90','format'] as const).map(window=>({window,available:true,points:[{date:'2026-09-20',usage_percent:20,sample_size:100,included_decks:20},{date:'2026-09-23',usage_percent:25,sample_size:120,included_decks:30}]}))}
const advance=async(ms:number)=>{await act(async()=>{vi.advanceTimersByTime(ms)})}
function mount(list=false,competitive=true){return render(<MemoryRouter><CompetitiveProvider><CardTile card={card} list={list} competitive={competitive}/></CompetitiveProvider></MemoryRouter>)}
beforeEach(()=>{HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','')};HTMLDialogElement.prototype.close=function(){this.removeAttribute('open')};vi.useFakeTimers();vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>data}))})
afterEach(()=>{cleanup();vi.useRealTimers();vi.unstubAllGlobals()})

test.each([false,true])('Library hover waits exactly 500ms, top five only; list=%s',async list=>{
 const view=mount(list),tile=view.container.querySelector('img')!
 fireEvent.pointerEnter(tile);await advance(499)
 expect(screen.queryByRole('dialog')).toBeNull();expect(fetch).not.toHaveBeenCalled()
 await advance(1)
 expect(screen.getByRole('dialog')).toBeInTheDocument()
 expect(screen.getAllByRole('listitem')).toHaveLength(5)
 expect(fetch).toHaveBeenCalledWith(expect.stringContaining('window=30&source=limitless-main&trend=false'),expect.anything())
 expect(screen.queryByText('Archetype 5')).toBeNull()
})
test('early leave cancels and crossing to popup preserves it until grace expires',async()=>{
 const view=mount(),tile=view.container.querySelector('img')!
 fireEvent.pointerEnter(tile);await advance(400);fireEvent.pointerLeave(tile);await advance(500)
 expect(fetch).not.toHaveBeenCalled()
 fireEvent.pointerEnter(tile);await advance(500)
 fireEvent.pointerLeave(tile);await advance(100);fireEvent.pointerEnter(screen.getByRole('dialog'));await advance(300)
 expect(screen.getByRole('dialog')).toBeInTheDocument()
 fireEvent.scroll(screen.getByRole('dialog'));expect(screen.getByRole('dialog')).toBeInTheDocument()
 fireEvent.pointerLeave(screen.getByRole('dialog'));await advance(179);expect(screen.getByRole('dialog')).toBeInTheDocument()
 await advance(1);expect(screen.queryByRole('dialog')).toBeNull()
})
test('non-Library tiles never request competitive hover',async()=>{
 const view=mount(false,false);fireEvent.pointerEnter(view.container.querySelector('img')!);await advance(2000)
 expect(fetch).not.toHaveBeenCalled();expect(screen.queryByRole('dialog')).toBeNull()
})
test('dashboard is continuous, threshold state and all trend series persist across window switch',async()=>{
 vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>({...data,archetypes:data.top_archetypes})} as Response)
 const view=render(<MemoryRouter><CompetitiveProvider><CompetitiveDashboard id="test-1"/></CompetitiveProvider></MemoryRouter>);await advance(0)
 expect(screen.getAllByText('Insufficient sample for prevalence — 14 decklists')).toHaveLength(6)
 expect(view.container.querySelectorAll('[data-series]')).toHaveLength(4)
 expect(screen.queryByRole('tab')).toBeNull()
 fireEvent.click(screen.getAllByRole('button',{name:'7D'})[0]);await advance(0)
 expect(fetch).toHaveBeenLastCalledWith(expect.stringContaining('window=7'),expect.anything())
 expect(view.container.querySelectorAll('[data-series]')).toHaveLength(4)
 expect(screen.getByRole('heading',{name:'Evidence / Dataset'})).toBeInTheDocument()
 expect([...view.container.querySelectorAll('.competitive-dashboard h3')].map(h=>h.textContent)).toEqual(['Competitive Overview','Copy Distribution','Usage Trend','Archetypes','Associated Cards','Evidence / Dataset'])
})
test('unavailable Format is disabled and observed zero is displayed',async()=>{
 vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>({...data,format_available:false,usage_percent:0})} as Response)
 render(<MemoryRouter><CompetitiveProvider><CompetitiveDashboard id="test-1"/></CompetitiveProvider></MemoryRouter>);await advance(0)
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
 const owned={...card,ownership:{functional_id:'f1',library_id:'l1',variant:'normal',quantity:0,functional_total:0,library_total:0}}
 vi.mocked(fetch).mockImplementation(async input=>({ok:true,json:async()=>String(input).includes('/competitive/')?data:{card:owned,source:'TCGdex',checked_at:'today',fetched_at:'today'}} as Response))
 const view=render(<MemoryRouter initialEntries={['/cards/test-1']}><Routes><Route path="/cards/:printingId" element={<CardDetail/>}/></Routes></MemoryRouter>);await advance(0)
 const art=view.container.querySelector('.detail-art')!;fireEvent.pointerEnter(art);await advance(1500)
 expect(screen.queryByRole('dialog')).toBeNull();expect(screen.getByText('Click to enlarge')).toBeInTheDocument()
 fireEvent.click(screen.getByRole('button',{name:/enlarge/i}));expect(screen.getByRole('dialog')).toBeInTheDocument()
 expect(view.container.querySelector('.competitive-popup')).toBeNull()
 const variations=screen.getByRole('button',{name:'Variations'})
 expect(variations.closest('.detail-art')).toBe(art)
 expect(variations.closest('.competitive-dashboard')).toBeNull()
})

test('archetype insufficient sample uses singular and plural; 15 reports prevalence',async()=>{
 const archetypes=[1,14,15].map(n=>({...data.top_archetypes[0],id:String(n),name:`Group ${n}`,eligible_decks:n,status:n<15?'insufficient_sample':'observed',prevalence_percent:n<15?null:20}))
 vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>({...data,archetypes})} as Response)
 const view=render(<MemoryRouter><CompetitiveDashboard id="test-1"/></MemoryRouter>);await advance(0)
 expect(screen.getByText('Insufficient sample for prevalence — 1 decklist')).toBeInTheDocument()
 expect(screen.getByText('Insufficient sample for prevalence — 14 decklists')).toBeInTheDocument()
 expect(view.container.querySelectorAll('tbody tr')[2]).toHaveTextContent('Group 1515%20%15')
})

test('average copies and percentages are presentation-rounded in popup, dashboard and trend',async()=>{
 const values={...data,average_copies:1.5611,usage_percent:43.4600,trend:data.trend.map(s=>({...s,points:s.points.map(p=>({...p,usage_percent:43.4667}))}))}
 vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>values} as Response)
 const view=mount();fireEvent.pointerEnter(view.container.querySelector('img')!);await advance(500)
 expect(screen.getByText('1.56')).toBeInTheDocument();expect(screen.getByText('43.46%')).toBeInTheDocument()
 view.unmount()
 render(<MemoryRouter><CompetitiveDashboard id="test-1"/></MemoryRouter>);await advance(0)
 expect(screen.getByText('1.56')).toBeInTheDocument();expect(screen.getByText('43.46%')).toBeInTheDocument()
 const point=screen.getByLabelText('7D 2026-09-20: 43.47% of 100 eligible decklists')
 expect(point.querySelector('title')).toHaveTextContent('43.47%');fireEvent.focus(point)
 expect(screen.getByText('7D: 43.47% · 100 eligible decklists')).toBeInTheDocument()
 expect(values.average_copies).toBe(1.5611);expect(values.trend[0].points[0].usage_percent).toBe(43.4667)
})

test('trend axis uses explicit Format range without adding observations',()=>{
 const view=render(<UsageTrend series={data.trend} start="2026-01-01" end="2026-09-24"/>)
 expect(screen.getByText('2026-01-01')).toBeInTheDocument();expect(screen.getByText('2026-09-24')).toBeInTheDocument()
 expect(view.container.querySelectorAll('circle')).toHaveLength(8)
 expect(view.container.querySelectorAll('[data-series]')).toHaveLength(4)
})

test('Associated Card name opens only a readable image preview, with no API call',async()=>{
 const associated_cards=[{functional_id:'dragapult',name:'Dragapult ex',image_url:'https://assets.tcgdex.net/en/sv/sv06/130/high.webp',printing_id:'sv06-130',decks:10,cooccurrence_percent:50,field_percent:20,lift:2.5}]
 vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>({...data,associated_cards})} as Response)
 render(<MemoryRouter><CompetitiveDashboard id="test-1"/></MemoryRouter>);await advance(0)
 const calls=vi.mocked(fetch).mock.calls.length
 expect(screen.queryByRole('img',{name:'Dragapult ex card artwork'})).toBeNull()
 fireEvent.pointerEnter(screen.getByRole('button',{name:'Dragapult ex'}))
 expect(screen.getByRole('img',{name:'Dragapult ex card artwork'})).toHaveAttribute('src',associated_cards[0].image_url)
 expect(screen.getByRole('tooltip')).not.toHaveTextContent('Usage')
 expect(screen.queryByRole('dialog')).toBeNull();expect(fetch).toHaveBeenCalledTimes(calls)
 fireEvent.keyDown(window,{key:'Escape'});expect(screen.queryByRole('tooltip')).toBeNull()
 fireEvent.focus(screen.getByRole('button',{name:'Dragapult ex'}))
 fireEvent.error(screen.getByRole('img',{name:'Dragapult ex card artwork'}));expect(screen.getByText('Image unavailable')).toBeInTheDocument()
})

test('stale backend contracts cannot masquerade as insufficient samples or missing artwork',async()=>{
 const legacy={...data,archetype_prevalence_min_decks:undefined}
 vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>legacy} as Response)
 render(<MemoryRouter><CompetitiveDashboard id="test-1"/></MemoryRouter>);await advance(0)
 expect(screen.getByRole('alert')).toHaveTextContent('competitive API is out of date')
 expect(screen.queryByRole('heading',{name:'Archetypes'})).toBeNull()
})

test('threshold explanation comes from API and genuinely missing artwork uses fallback',async()=>{
 const associated_cards=[{functional_id:'missing',name:'Missing artwork',image_url:null,printing_id:null,decks:3,cooccurrence_percent:20,field_percent:10,lift:2}]
 vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>({...data,archetype_prevalence_min_decks:27,associated_cards})} as Response)
 render(<MemoryRouter><CompetitiveDashboard id="test-1"/></MemoryRouter>);await advance(0)
 expect(screen.getByText(/at least 27 eligible archetype decklists/)).toBeInTheDocument()
 fireEvent.pointerEnter(screen.getByRole('button',{name:'Missing artwork'}))
 expect(screen.getByRole('tooltip')).toHaveTextContent('Image unavailable')
 expect(screen.queryByRole('img',{name:'Missing artwork card artwork'})).toBeNull()
})

test.each([0,4,14,15])('Phase 6 explores %s eligible decks without weakening prevalence threshold',async n=>{
 const archetype={id:'/decks/284',research_id:'stable-key',name:'Fixture Archetype',decks:1,eligible_decks:n,share_percent:100,prevalence_percent:n>=15?20:null,status:n>=15?'observed':'insufficient_sample'}
 vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>({...data,archetypes:[archetype]})} as Response)
 render(<MemoryRouter initialEntries={['/cards/test-1?window=90']}><CompetitiveProvider><CompetitiveDashboard id="test-1"/></CompetitiveProvider></MemoryRouter>);await advance(0)
 expect(screen.getByRole('link',{name:'Fixture Archetype'})).toHaveAttribute('href','/archetypes/stable-key?window=90')
 if(n){expect(screen.getByRole('link',{name:`Explore ${n} decks →`})).toHaveAttribute('href','/archetypes/stable-key?window=90#tournament-evidence')}
 else expect(screen.queryByRole('link',{name:/Explore/})).toBeNull()
 if(n<15)expect(screen.getByText(`Insufficient sample for prevalence — ${n} decklists`)).toBeInTheDocument()
 else expect(screen.queryByText(/Insufficient sample for prevalence/)).toBeNull()
})
