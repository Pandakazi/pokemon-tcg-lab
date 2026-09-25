import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, expect, test, vi } from 'vitest'
import { CardImage, CardTile } from './CardTile'
import { DeckProvider, DeckControls, type Workspace } from './DeckBuilder'
import type { Card } from './api'

const card:Card={id:'test-1',name:'Test',deck_identity:'f',category:'Pokemon',legal:{standard:true},localId:'1',set:{id:'test'},image_url:'/first/high.webp',legality_provenance:{source:'TCGdex',checked_at:'today'},ownership:{functional_id:'f',library_id:'l',variant:'normal',quantity:0,functional_total:0,library_total:0}}
const other:Card={...card,id:'test-2',image_url:'/second/high.webp',ownership:{...card.ownership!,variant:'reverse'}}
afterEach(()=>{vi.useRealTimers();vi.unstubAllGlobals()})

test('failed artwork state resets for a new image resource, with bounded same-printing fallback',()=>{
 const view=render(<CardImage card={card} eager/>)
 fireEvent.error(screen.getByRole('img'));expect(screen.getByRole('img')).toHaveAttribute('src','/first/low.webp')
 fireEvent.error(screen.getByRole('img'));expect(screen.getByText('Image unavailable')).toBeInTheDocument()
 view.rerender(<CardImage card={other} eager/>)
 expect(screen.getByRole('img')).toHaveAttribute('src','/second/high.webp')
 expect(screen.queryByText('Image unavailable')).toBeNull()
 view.rerender(<CardImage card={{...other,image_url:null}} eager/>)
 expect(screen.getByText('Image unavailable')).toBeInTheDocument()
})

test.each([false,true])('only actual artwork starts shared competitive hover in list=%s',async list=>{
 vi.useFakeTimers();vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,json:async()=>({})}))
 const view=render(<MemoryRouter><CardTile card={card} competitive list/></MemoryRouter>)
 const nodes=view.container.querySelectorAll('article,.card-link,strong,.printing,code,.card-details,small,button,.card-art')
 for(const node of nodes){fireEvent.pointerEnter(node);await act(async()=>{vi.advanceTimersByTime(600)});expect(screen.queryByRole('dialog')).toBeNull();fireEvent.pointerLeave(node)}
 expect(fetch).not.toHaveBeenCalled()
 const art=view.container.querySelector('img')!
 fireEvent.pointerEnter(art);await act(async()=>{vi.advanceTimersByTime(499)});expect(screen.queryByRole('dialog')).toBeNull()
 await act(async()=>{vi.advanceTimersByTime(1)});expect(screen.getByRole('dialog')).toBeInTheDocument()
 expect(screen.queryByText(/Cards? in deck/)).toBeNull()
})

test('exact controls, independent default, and live bold hover aggregate across printings',async()=>{
 let state:Workspace={schema_version:2,revision:0,defaults:{},deck:{id:'d',name:'Draft',format:'standard',entries:[],has_saved:false,dirty:false},validation:{state:'EMPTY',total:0,categories:{},reasons:[],unknown:[],limitations:[]},saved:[]}
 const commands:any[]=[]
 vi.stubGlobal('fetch',vi.fn(async(url:string,init?:RequestInit)=>{
  if(url!='/api/v1/deck-workspace')return {ok:false,json:async()=>({})}
  if(init){
   const body=JSON.parse(init.body as string);commands.push(body)
   expect(body.schema_version).toBe(2)
   state=structuredClone(state);state.revision++
   if(body.action==='default_printing')state.defaults.f={printing_id:body.printing_id,variant:body.variant,available:true}
   else{
    const entry=state.deck.entries[0]||{identity:'f',quantity:0,allocations:[],printing_id:card.id,variant:'normal',name:'Test',category:'Pokemon',presentation_available:true,owned:card.ownership!}
    let allocation=entry.allocations.find(a=>a.printing_id===body.printing_id&&a.variant===body.variant)
    if(!allocation){allocation={printing_id:body.printing_id,variant:body.variant,quantity:0,available:true,owned:card.ownership!};entry.allocations.push(allocation)}
    allocation.quantity+=body.delta;entry.quantity+=body.delta;state.deck.entries=[entry]
   }
  }
  return {ok:true,json:async()=>structuredClone(state)}
 }))
 const view=render(<MemoryRouter initialEntries={['/deck-builder']}><DeckProvider>
  <div data-testid="a"><DeckControls card={card} exact/></div>
  <div data-testid="b"><DeckControls card={other} exact/></div>
  <CardTile card={card} competitive/><CardTile card={other} competitive/>
 </DeckProvider></MemoryRouter>)
 const a=within(screen.getByTestId('a')),b=within(screen.getByTestId('b'))
 await waitFor(()=>expect(a.getByRole('button',{name:'Add Test to deck'})).toBeEnabled())
 vi.useFakeTimers()
 const hover=async(index:number)=>{fireEvent.pointerEnter(view.container.querySelectorAll('img')[index]);await act(async()=>{vi.advanceTimersByTime(500)})}
 const leave=async()=>{fireEvent.pointerLeave(view.container.querySelectorAll('img')[0]);fireEvent.pointerLeave(view.container.querySelectorAll('img')[1]);await act(async()=>{vi.advanceTimersByTime(180)})}
 await hover(0);expect(screen.getByText('0 Cards in deck').tagName).toBe('STRONG')
 await act(async()=>{fireEvent.click(a.getByRole('button',{name:'Add Test to deck'}))})
 expect(screen.getByText('1 Card in deck').tagName).toBe('STRONG')
 await act(async()=>{fireEvent.click(b.getByRole('button',{name:'Add Test to deck'}));fireEvent.click(b.getByRole('button',{name:'Add Test to deck'}))})
 expect(screen.getByText('3 Cards in deck').tagName).toBe('STRONG')
 expect(a.getByRole('status')).toHaveTextContent('1');expect(b.getByRole('status')).toHaveTextContent('2')
 expect(a.getByText('Total in deck: 3')).toBeInTheDocument();expect(b.getByText('Total in deck: 3')).toBeInTheDocument()
 await leave();await hover(1);expect(screen.getByText('3 Cards in deck')).toBeInTheDocument()
 expect(screen.queryByRole('button',{name:/Default printing|default printing/})).toBeNull()
 expect(commands.filter(c=>c.action==='quantity').every(c=>c.exact)).toBe(true)
})
