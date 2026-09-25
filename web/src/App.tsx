import { useEffect, useRef, useState } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation, useNavigate, useSearchParams } from 'react-router'
import { LibraryControls, TopBar } from './Shell'
import { loadCards, withOwnership, type CardPage, type FilterOption, type Ownership } from './api'
import { CardTile } from './CardTile'
import { Filters, filterFamilies, abilityValues } from './Filters'
import { CardDetail } from './CardDetail'
import { CollectionPage } from './CollectionPage'
import { CompetitiveProvider, CompetitiveWindows } from './Competitive'
import { DeckProvider, DeckTray, useBuilder } from './DeckBuilder'
import { ArchetypeResearch, TournamentDeckResearch } from './ResearchPages'

type CategoryMemory = {current:Record<string,string>;filterOpen?:boolean;scroll?:Record<string,number>}
function Library({view,setView,memory}:{view:'gallery'|'list';setView:(v:'gallery'|'list')=>void;memory:CategoryMemory}) {
 const [params,setParams]=useSearchParams()
 const [filterOpen,setFilterOpen]=useState(memory.filterOpen??true)
 const scroll=useRef<HTMLElement>(null)
 const builder=useBuilder()
 const [attempt,setAttempt]=useState(0)
 const [result,setData]=useState<CardPage|null>(null)
 const [resolvedQuery,setResolvedQuery]=useState<string|null>(null)
 const [options,setOptions]=useState<FilterOption[]>([])
 const [error,setError]=useState('')
 const [pending,setLoading]=useState(true)
 const query=params.toString(), category=params.get('category') || 'Pokemon'
 const latestQuery=useRef(query)
 useEffect(()=>{latestQuery.current=query;memory.current[category]=query},[query,category,memory])
 // Never render links from the previous query while URL state is changing.
 const data=resolvedQuery===query?result:null
 useEffect(()=>{if(data&&scroll.current)scroll.current.scrollTop=memory.scroll?.[query]||0},[data,query,memory])
 const loading=pending || resolvedQuery!==query
 const page=Number(params.get('page') || 1)
 useEffect(()=>{
  const controller=new AbortController()
  if(resolvedQuery!==query) {setLoading(true);setData(null)}
  setError('')
  const timer=setTimeout(()=>loadCards(new URLSearchParams(query),controller.signal).then(result=>{
   if(!controller.signal.aborted) {setData(result);setResolvedQuery(query);setOptions(result.filter_options || [])}
  }).catch(reason=>{
   if(!controller.signal.aborted) {setError(reason instanceof Error?reason.message:'Unable to reach the card API.');setResolvedQuery(query)}
  }).finally(()=>{if(!controller.signal.aborted)setLoading(false)}),150)
  return ()=>{clearTimeout(timer);controller.abort()}
 },[query,attempt])
 const update=(fn:(next:URLSearchParams)=>void,replace=false)=>{
  const next=new URLSearchParams(latestQuery.current);next.delete('page');fn(next)
  latestQuery.current=next.toString();setParams(next,{replace})
 }
 const changeCategory=(value:string)=>{
  const target=({pokemon:'Pokemon',trainers:'Trainer',energy:'Energy'} as Record<string,string>)[value]
  if(target===category)return
  memory.current[category]=latestQuery.current
  const next=new URLSearchParams(memory.current[target] || `category=${target}`)
  next.set('category',target);latestQuery.current=next.toString();setOptions([]);setParams(next)
 }
 const toggle=(key:string,value:string)=>update(next=>{
  if(key==='ability') {
   const selected=abilityValues(next);next.delete('has_ability');next.delete('ability')
   selected.forEach(v=>next.append('ability',v))
  }
  const values=next.getAll(key);next.delete(key)
  const selected=values.includes(value)?values.filter(v=>v!==value):[...values,value]
  selected.forEach(v=>next.append(key,v))
 })
 const clear=()=>update(next=>filterFamilies.forEach(key=>next.delete(key)))
 const changed=(id:string,o:Ownership)=>{setData(old=>old?{...old,cards:old.cards.map(c=>withOwnership(c,id,o))}:old);setAttempt(v=>v+1)}
 return <>
  {filterOpen && <Filters options={options} params={params} onChange={toggle} onClear={clear}/>}
  <main>
   <h1 className="sr-only">Card library</h1>
   <LibraryControls category={category==='Trainer'?'trainers':category==='Energy'?'energy':'pokemon'} onCategoryChange={changeCategory}
    scope={(params.get('ownership')||'all') as 'all'|'owned'|'unowned'} onScopeChange={scope=>update(next=>{scope==='all'?next.delete('ownership'):next.set('ownership',scope)})} viewMode={view} onViewModeChange={setView}
    searchQuery={params.get('q') || ''} onSearchChange={q=>update(next=>{q?next.set('q',q):next.delete('q')},true)}
    filterOpen={filterOpen} onFilterToggle={()=>setFilterOpen(v=>{memory.filterOpen=!v;return !v})} totalCards={data?.total??0} filteredCount={data?Math.min((data.page-1)*data.page_size+data.cards.length,data.total):0}/>
   <div className="source-note">TCGdex · local SQLite · Standard {category==='Pokemon'?'Pokémon':category}
    {data && <span> · Sync: {data.sync.status}{data.sync.finished_at?` · ${data.sync.finished_at.slice(0,10)}`:''}</span>}
   </div>
   <CompetitiveWindows/>
   <section ref={scroll} onScroll={e=>{if(data){memory.scroll??={};memory.scroll[query]=e.currentTarget.scrollTop}}} className="gallery-scroll" aria-label="Card library results" aria-busy={loading}>
    {loading && <p role="status">Loading cards…</p>}
    {error && resolvedQuery===query && <div role="alert"><h2>Cards could not be loaded</h2><p>{error}</p><button onClick={()=>setAttempt(v=>v+1)}>Retry</button> <Link to={builder?'/deck-builder':'/'}>Reset library query</Link></div>}
    {data && !data.cards.length && <p role="status">No cards match this query.</p>}
    {data && <div className={view==='gallery'?'card-grid':'card-list'}>
     {view==='list' && <div className="list-heading" aria-hidden="true"><span>Card</span><span>Name</span><span>Set · Number</span><span>Printing ID</span><span>Classification</span><span>Legality</span></div>}
     {data.cards.map(card=><CardTile key={card.id} card={card} competitive list={view==='list'} onChange={changed} onPreference={()=>setAttempt(v=>v+1)}/>)}</div>}
   </section>
   <nav className="pagination" aria-label="Pagination">
    <button disabled={loading || page<=1} onClick={()=>{const next=new URLSearchParams(params);next.set('page',String(page-1));setParams(next)}}>Previous</button>
    <span>Page {page}{data?` of ${Math.max(1,Math.ceil(data.total/data.page_size))}`:''}</span>
    <button disabled={loading || !data?.next_page} onClick={()=>{const next=new URLSearchParams(params);next.set('page',String(data!.next_page));setParams(next)}}>Next</button>
   </nav>
  </main>
 </>
}
function ApplicationWorkspace() {
 const categoryMemory=useRef<Record<string,string>>({})
 const builderMemory=useRef<Record<string,string>>({})
 const [agentOpen,setAgentOpen]=useState(true)
 const [builderAgentOpen,setBuilderAgentOpen]=useState(false)
 const [view,setView]=useState<'gallery'|'list'>('gallery')
 const [builderView,setBuilderView]=useState<'gallery'|'list'>('gallery')
 const builder=useBuilder()
 const panelOpen=builder?builderAgentOpen:agentOpen
 const navigate=useNavigate(), location=useLocation()
 const lastLibrary=useRef('/'),lastCollection=useRef('/collection'),lastBuilder=useRef('/deck-builder')
 useEffect(()=>{if(location.pathname==='/')lastLibrary.current='/'+location.search;if(location.pathname==='/collection')lastCollection.current='/collection'+location.search;if(location.pathname==='/deck-builder')lastBuilder.current='/deck-builder'+location.search},[location])
 return <div className={`mica-bg app-shell ${builder?'builder-workspace':''}`}><TopBar activeNav={builder?'Deck Builder':location.pathname==='/collection'?'Collection':'Library'} onNavChange={nav=>navigate(nav==='Home'?'/':nav==='Deck Builder'?lastBuilder.current:nav==='Collection'?lastCollection.current:lastLibrary.current)}/>
  <div className="workspace"><Routes>
   <Route path="/" element={<Library view={view} setView={setView} memory={categoryMemory}/>}/>
   <Route path="/cards/:printingId" element={<CardDetail/>}/>
   <Route path="/collection" element={<CollectionPage/>}/>
   <Route path="/deck-builder" element={<Library key="builder" view={builderView} setView={setBuilderView} memory={builderMemory}/>}/>
   <Route path="/deck-builder/cards/:printingId" element={<CardDetail/>}/>
   <Route path="/archetypes/:key" element={<ArchetypeResearch/>}/>
   <Route path="/tournament-decks/:key" element={<TournamentDeckResearch/>}/>
   <Route path="/deck-builder/archetypes/:key" element={<ArchetypeResearch/>}/>
   <Route path="/deck-builder/tournament-decks/:key" element={<TournamentDeckResearch/>}/>
   <Route path="*" element={<main className="gallery-scroll"><h1>Page not found</h1><Link to="/">Open library</Link></main>}/>
  </Routes>
  <DeckTray/>
  <aside className={`agent-panel ${panelOpen?'':'collapsed'}`} aria-label="PokéLab Agent">
   <button aria-label="Toggle Agent panel" aria-expanded={panelOpen} onClick={()=>builder?setBuilderAgentOpen(v=>!v):setAgentOpen(v=>!v)}>{panelOpen?'PokéLab Agent  ›':'‹'}</button>
   {panelOpen && <p>The Agent workspace is preserved for a later slice. No AI provider is connected.</p>}
  </aside></div>
 </div>
}
export function Application() {return <DeckProvider><ApplicationWorkspace/></DeckProvider>}
// Query controls must update synchronously with the URL, not in a delayed transition.
export default function App() {return <BrowserRouter useTransitions={false}><CompetitiveProvider><Application/></CompetitiveProvider></BrowserRouter>}
