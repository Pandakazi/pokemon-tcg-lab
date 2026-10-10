import {render,screen,fireEvent,waitFor,within} from '@testing-library/react'
import {MemoryRouter,Routes,Route,useSearchParams} from 'react-router'
import {test,expect,vi} from 'vitest'
import {CompetitiveSync,freshness} from './CompetitiveSync'
import {AgentMarkdown} from './AgentMarkdown'
import {TopBar} from './Shell'
import {CardDetail} from './CardDetail'
import {CollectionPage} from './CollectionPage'
import {orderedDeck,deckListText} from './DeckListText'

const ok=(body:unknown)=>({ok:true,status:200,json:async()=>body})
test('manual sync is explicit, single-flight, success disables cooldown and displays freshness',async()=>{
 let release!:(value:unknown)=>void
 const fetch=vi.fn(async(_url:string,options?:RequestInit)=>options?.method==='POST'?new Promise(resolve=>{release=resolve}):ok({status:'ready',last_successful_at:null}))
 vi.stubGlobal('fetch',fetch);render(<CompetitiveSync/>)
 const button=screen.getByRole('button',{name:'Sync Competitive Data'})
 await waitFor(()=>expect(button).toBeEnabled());expect(fetch).toHaveBeenCalledTimes(1)
 fireEvent.click(button);fireEvent.click(button)
 expect(screen.getByRole('button',{name:'Syncing…'})).toBeDisabled()
 expect(fetch).toHaveBeenCalledTimes(2)
 const timestamp=new Date().toISOString()
 release(ok({status:'complete',last_successful_at:timestamp,available_at:new Date(Date.now()+3600000).toISOString()}))
 await screen.findByText(/synced just now/)
 expect(screen.getByRole('button',{name:'Sync Competitive Data'})).toBeDisabled()
 expect(screen.getByText(/Available again in 60m/)).toBeVisible()
 expect(screen.getByText(/synced just now/)).toHaveAttribute('title')
})
test('failed manual sync preserves successful freshness and shows concise failure',async()=>{
 const last=new Date(Date.now()-18*60000).toISOString()
 vi.stubGlobal('fetch',vi.fn(async(_url:string,o?:RequestInit)=>o?.method==='POST'?{ok:false,status:503,json:async()=>({status:'failed'})}:ok({status:'ready',last_successful_at:last})))
 render(<CompetitiveSync/>);const button=screen.getByRole('button',{name:'Sync Competitive Data'})
 await waitFor(()=>expect(button).toBeEnabled());fireEvent.click(button)
 expect(await screen.findByRole('alert')).toHaveTextContent('previous data is still available')
 expect(screen.getByText(/synced 18m ago/)).toBeVisible();expect(button).toBeEnabled()
})
test('freshness supports relative and older exact dates',()=>{
 const now=Date.parse('2026-10-10T12:00:00Z')
 expect(freshness(null,now)).toBe('not synced yet')
 expect(freshness('2026-10-10T11:42:00Z',now)).toBe('synced 18m ago')
 expect(freshness('2026-10-09T11:00:00Z',now)).toContain('Oct')
})
test('escaped headings, emphasis and lists render safely without HTML execution',()=>{
 render(<AgentMarkdown text={'\\### Setup\n\\*\\*Consistency\\*\\* matters.\n\n\\* First option\n* Second *option*\n\n<img src=x onerror=alert(1)>'} cards={[]} inspect={()=>{}}/>)
 expect(screen.getByRole('heading',{name:'Setup'})).toBeVisible()
 expect(screen.getByText('Consistency').tagName).toBe('STRONG')
 expect(screen.getAllByRole('listitem')).toHaveLength(2)
 expect(screen.getByText('option').tagName).toBe('EM')
 expect(screen.queryByRole('img')).toBeNull()
 expect(document.body.textContent).not.toContain('\\###')
})
test('category sorting/copy preserves exact identities, counts and source array',()=>{
 const rows=[{category:'Energy',canonical_name:'Fire Energy',printing_id:'sv-1',quantity:9},{category:'Trainer',canonical_name:'Ultra Ball',printing_id:'sv-2',quantity:32},{category:'Pokemon',canonical_name:'Dragapult ex',printing_id:'sv-3',quantity:19}]
 const before=JSON.stringify(rows),sorted=orderedDeck(rows),text=deckListText(rows)
 expect(sorted.map(c=>c.category)).toEqual(['Pokemon','Trainer','Energy'])
 expect(text).toBe('Pokémon: 19\n19 Dragapult ex (sv-3)\n\nTrainer: 32\n32 Ultra Ball (sv-2)\n\nEnergy: 9\n9 Fire Energy (sv-1)\n\nTotal Cards: 60')
 expect(JSON.stringify(rows)).toBe(before)
})
test('Analytics retains disabled native tooltip and cannot navigate',()=>{
 const navigate=vi.fn();render(<TopBar activeNav="Library" onNavChange={navigate}/>)
 const analytics=screen.getByRole('button',{name:'Analytics'})
 expect(analytics).toBeDisabled();expect(analytics.parentElement).toHaveAttribute('title','Coming soon!')
 fireEvent.click(analytics);expect(navigate).not.toHaveBeenCalled()
})
test('illustrator link goes to Gallery filter without modifying collection or deck',async()=>{
 const card={id:'sv-3',name:'Dragapult ex',category:'Pokemon',localId:'3',set:{id:'sv'},legal:{standard:true},illustrator:'Atsushi Furusawa',legality_provenance:{source:'TCGdex',checked_at:'today'}}
 const fetch=vi.fn(async(_url:string,_options?:RequestInit)=>ok({card,source:'TCGdex',checked_at:'today',fetched_at:'today'}));vi.stubGlobal('fetch',fetch)
 function Gallery(){const [params]=useSearchParams();return <p>Illustrator = {params.get('illustrators')}</p>}
 render(<MemoryRouter initialEntries={['/cards/sv-3']}><Routes><Route path="/cards/:printingId" element={<CardDetail/>}/><Route path="/" element={<Gallery/>}/></Routes></MemoryRouter>)
 const link=await screen.findByRole('link',{name:'Atsushi Furusawa'});fireEvent.click(link)
 expect(link).toHaveAttribute('href','/?illustrators=Atsushi+Furusawa')
 expect(await screen.findByText('Illustrator = Atsushi Furusawa')).toBeVisible()
 expect(fetch.mock.calls.every(args=>!args[1]||!(args[1] as RequestInit).method)).toBe(true)
})
test('collection artist filter is shareable and clearable',async()=>{
 const fetch=vi.fn(async()=>ok({cards:[],page:1,page_size:24,total:0,next_page:null}));vi.stubGlobal('fetch',fetch)
 render(<MemoryRouter initialEntries={['/collection?illustrators=Atsushi+Furusawa']}><CollectionPage/></MemoryRouter>)
 await screen.findByText(/No indexed printings match/)
 expect(screen.getByRole('textbox',{name:'Illustrator'})).toHaveValue('Atsushi Furusawa')
 expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/cards?illustrators=Atsushi+Furusawa'),expect.anything())
 fireEvent.click(screen.getByRole('button',{name:'Clear illustrator'}))
 await waitFor(()=>expect(fetch).toHaveBeenLastCalledWith('/api/v1/collection?page_size=24',expect.anything()))
})
