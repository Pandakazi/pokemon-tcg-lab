import { MemoryRouter } from 'react-router'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { test, expect, vi } from 'vitest'
import { Application } from './App'
import { CompetitiveProvider } from './Competitive'
import type { Workspace } from './DeckBuilder'
import type { Card } from './api'

const card:Card={id:'test-1',name:'Test Basic',deck_identity:'functional-test',category:'Pokemon',localId:'1',set:{id:'test'},legal:{standard:true},legality_provenance:{source:'TCGdex',checked_at:'2026-09-25'},ownership:{functional_id:'functional-test',library_id:'library-test',variant:'normal',quantity:2,functional_total:3,library_total:3}}
const fresh=():Workspace=>({schema_version:1,revision:0,deck:{id:'draft',name:'New Deck',format:'standard',entries:[],has_saved:false,dirty:false},validation:{state:'EMPTY',total:0,categories:{},reasons:[],unknown:[],limitations:[]},saved:[]})
function setup(path='/deck-builder',intercept?:(body:any)=>Promise<void>){
 let workspace=fresh()
 const fetch=vi.fn(async(url:string,options?:RequestInit)=>{
  let result:any
  if(url==='/api/v1/deck-workspace'){
   if(options?.method==='POST'){
    const body=JSON.parse(options.body as string);await intercept?.(body)
    expect(body.revision).toBe(workspace.revision)
    const quantity=(workspace.deck.entries[0]?.quantity||0)+(body.delta||0)
    workspace={...workspace,revision:workspace.revision+1,deck:{...workspace.deck,dirty:true,entries:quantity?[{identity:card.deck_identity!,printing_id:card.id,variant:'normal',quantity,name:card.name,category:card.category,presentation_available:true,owned:card.ownership!}]:[]}}
   }
   result=workspace
  }else if(url.includes('/variations'))result={cards:[card],unassigned:[{...card,ownership:{...card.ownership!,variant:'unspecified'}}],total:1,page:1,page_size:24,next_page:null}
  else if(url.startsWith('/api/v1/cards/test-1?'))result={card,source:'TCGdex',checked_at:'today',fetched_at:'today',game:'tcg'}
  else if(url.startsWith('/api/v1/competitive'))return {ok:false,status:503,json:async()=>({})}
  else result={cards:[card],page:1,page_size:24,total:1,next_page:null,filter_options:[],sync:{status:'complete'}}
  return {ok:true,json:async()=>structuredClone(result)}
 })
 vi.stubGlobal('fetch',fetch)
 render(<MemoryRouter initialEntries={[path]}><CompetitiveProvider><Application/></CompetitiveProvider></MemoryRouter>)
 return fetch
}

test('builder gallery quantity changes only deck, with static ownership and shared hover component',async()=>{
 const fetch=setup()
 const plus=await screen.findByRole('button',{name:'Add Test Basic to deck'})
 await waitFor(()=>expect(plus).toBeEnabled())
 expect(screen.queryByRole('button',{name:/Add one/})).not.toBeInTheDocument()
 expect(screen.queryByText('Choose artwork / finish')).not.toBeInTheDocument()
 fireEvent.click(plus)
 await waitFor(()=>expect(screen.getByLabelText('Test Basic deck quantity')).toHaveTextContent('1'))
 expect(fetch.mock.calls.filter(([,o])=>o?.method==='POST')).toHaveLength(1)
 expect(fetch.mock.calls.some(([url])=>url.startsWith('/api/v1/collection'))).toBe(false)
 expect(screen.getByLabelText('PokéLab Agent')).toBeInTheDocument()
})

test('rapid quantity clicks are serialized using the last acknowledged revision',async()=>{
 let release!:()=>void,first=true
 const fetch=setup('/deck-builder',async()=>{if(first){first=false;await new Promise<void>(r=>release=r)}})
 const plus=await screen.findByRole('button',{name:'Add Test Basic to deck'});await waitFor(()=>expect(plus).toBeEnabled())
 fireEvent.click(plus);fireEvent.click(plus);fireEvent.click(plus)
 await waitFor(()=>expect(release).toBeTypeOf('function'))
 expect(fetch.mock.calls.filter(([,o])=>o?.method==='POST')).toHaveLength(1)
 release()
 await waitFor(()=>expect(screen.getByLabelText('Test Basic deck quantity')).toHaveTextContent('3'))
 const revisions=fetch.mock.calls.filter(([,o])=>o?.method==='POST').map(([,o])=>JSON.parse(o!.body as string).revision)
 expect(revisions).toEqual([0,1,2])
})

test('builder detail and variations never expose editable collection controls',async()=>{
 setup('/deck-builder/cards/test-1?variant=normal')
 expect(await screen.findByRole('heading',{name:'Test Basic'})).toBeInTheDocument()
 expect(screen.getByText('Function total: 3')).toBeInTheDocument()
 expect(screen.getByText('normal — this variation: 2')).toBeInTheDocument()
 fireEvent.click(screen.getByRole('button',{name:'Variations'}))
 await screen.findByRole('link',{name:'Inspect test-1 normal'})
 expect(screen.queryByRole('button',{name:/Add one|Remove one/})).not.toBeInTheDocument()
 expect(screen.getByRole('link',{name:'Inspect test-1 normal'})).toHaveAttribute('href','/deck-builder/cards/test-1?variant=normal')
 expect(screen.getByLabelText('Active deck')).toBeInTheDocument()
})

test('failed mutation is visible, stops queued writes, and reload reconciles stored draft',async()=>{
 const fetch=setup('/deck-builder',async()=>{throw new Error('Disk unavailable')})
 const plus=await screen.findByRole('button',{name:'Add Test Basic to deck'});await waitFor(()=>expect(plus).toBeEnabled())
 fireEvent.click(plus);fireEvent.click(plus)
 await waitFor(()=>expect(within(screen.getByLabelText('Active deck')).getByRole('alert')).toHaveTextContent('Disk unavailable'))
 expect(fetch.mock.calls.filter(([,o])=>o?.method==='POST')).toHaveLength(1)
 expect(plus).toBeDisabled()
 fireEvent.click(screen.getByRole('button',{name:'Reload stored draft'}))
 await waitFor(()=>expect(plus).toBeEnabled())
 expect(screen.getByLabelText('Test Basic deck quantity')).toHaveTextContent('0')
})

test('normal Library keeps its certified collection controls and logo goes Home',async()=>{
 setup('/')
 expect(await screen.findByRole('button',{name:'Add one test-1 normal'})).toBeInTheDocument()
 expect(screen.queryByRole('button',{name:'Add Test Basic to deck'})).not.toBeInTheDocument()
 fireEvent.click(screen.getByRole('button',{name:'Deck Builder'}))
 await screen.findByLabelText('Active deck')
 fireEvent.click(screen.getByRole('button',{name:'PokéLab Home'}))
 await waitFor(()=>expect(screen.queryByLabelText('Active deck')).not.toBeInTheDocument())
})

test('unfinished rename cannot be silently discarded by New or Open',async()=>{
 setup()
 const rename=await screen.findByRole('button',{name:'Rename'})
 await waitFor(()=>expect(rename).toBeEnabled());fireEvent.click(rename)
 fireEvent.change(screen.getByRole('textbox',{name:'Deck name'}),{target:{value:'Unapplied name'}})
 expect(screen.getByRole('button',{name:'New'})).toBeDisabled()
 expect(screen.getByRole('button',{name:'Open'})).toBeDisabled()
 expect(screen.getByRole('button',{name:'Save'})).toBeDisabled()
 fireEvent.click(screen.getByRole('button',{name:'Cancel'}))
 expect(screen.getByRole('button',{name:'New'})).toBeEnabled()
})
