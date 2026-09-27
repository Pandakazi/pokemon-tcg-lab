import {useState} from 'react'
import {MemoryRouter} from 'react-router'
import {render,screen,fireEvent,waitFor,within} from '@testing-library/react'
import {test,expect,vi} from 'vitest'
import {DeckProvider,useDeck} from './DeckBuilder'
import {CompetitiveProvider} from './Competitive'
import {ResearchAgentProvider,ResearchPanel,useResearchAgent} from './ResearchAgent'

function Harness(){
 const agent=useResearchAgent(),deck=useDeck(),[open,setOpen]=useState(true)
 return <><button onClick={()=>agent.select({printing:'budew-1',name:'Budew',identity:'budew',variant:'holo'})}>Select Budew</button>
 <button onClick={()=>agent.select({printing:'ruins-1',name:'Risky Ruins',identity:'ruins',variant:'normal'})}>Select Risky Ruins</button>
 <button onClick={()=>deck?.send({action:'remove',identity:'budew'})}>Remove Budew</button>
 <button onClick={()=>deck?.send({action:'new',discard:true})}>Change deck</button>
 <ResearchPanel open={open} toggle={()=>setOpen(v=>!v)}/></>
}
const answer={status:'answered',answer:{outcome:'answered',facts:[{text:'Captured deck fact.',evidence:['active-deck']}],interpretation:[],limitations:['Intent unknown.']}}
function setup(reply:()=>Promise<unknown>=async()=>answer){
 let revision=157,id='deck-1',removed=false
 const fetch=vi.fn(async(url:string,options?:RequestInit)=>{
  let result:unknown
  if(url==='/api/v1/agent/status')result={version:'pokelab-research-v1',available:true,provider:'gemini',model:'gemini-3.5-flash-lite',archetypes:[{id:'explicit-key',name:'Dragapult'}]}
  else if(url==='/api/v1/agent/research')result=await reply()
  else if(url==='/api/v1/deck-workspace'){
   if(options?.method==='POST'){
    const command=JSON.parse(options.body as string);revision++
    if(command.action==='new')id='deck-2'
    if(command.action==='remove')removed=true
   }
   result={schema_version:2,defaults:{},revision,deck:{id,name:'Test Deck',dirty:false,entries:(removed?['ruins']:['budew','ruins']).map(identity=>({identity,name:identity,quantity:1,allocations:[]}))},validation:{state:'IN PROGRESS',total:2,categories:{},reasons:[],unknown:[],limitations:[]},saved:[]}
  }else return {ok:false,json:async()=>({})}
  return {ok:true,json:async()=>result}
 })
 vi.stubGlobal('fetch',fetch)
 render(<MemoryRouter initialEntries={['/deck-builder']}><CompetitiveProvider><DeckProvider><ResearchAgentProvider><Harness/></ResearchAgentProvider></DeckProvider></CompetitiveProvider></MemoryRouter>)
 return fetch
}
const calls=(fetch:ReturnType<typeof setup>)=>fetch.mock.calls.filter(([url])=>url==='/api/v1/agent/research')
async function type(question='What is this deck trying to do?'){
 await screen.findByText(/Configured: gemini/)
 fireEvent.change(screen.getByRole('textbox'),{target:{value:question}})
 await waitFor(()=>expect(screen.getByRole('button',{name:'Ask'})).toBeEnabled())
}

test('deck level explicit Ask uses authoritative revision and explicit archetype; context-only actions cost zero calls',async()=>{
 const fetch=setup()
 await screen.findByText('Context: Active Deck')
 await screen.findByRole('option',{name:'Dragapult'})
 fireEvent.change(screen.getByLabelText('Comparison archetype'),{target:{value:'explicit-key'}})
 await type('How does this deck differ from typical Dragapult decks?')
 fireEvent.click(screen.getByRole('button',{name:'Toggle Agent panel'}));fireEvent.click(screen.getByRole('button',{name:'Toggle Agent panel'}))
 expect(calls(fetch)).toHaveLength(0)
 fireEvent.click(screen.getByRole('button',{name:'Ask'}))
 await screen.findByRole('article')
 expect(calls(fetch)).toHaveLength(1)
 expect(JSON.parse(calls(fetch)[0][1]!.body as string)).toEqual({scope:'active_deck_research',question:'How does this deck differ from typical Dragapult decks?',revision:157,window:'30',archetype:'explicit-key'})
})

test('selection, switching, deselection clear draft and preserve answer without inference',async()=>{
 const fetch=setup();await type();fireEvent.click(screen.getByRole('button',{name:'Ask'}));await screen.findByRole('article')
 await type('Unsubmitted deck question')
 fireEvent.click(screen.getByRole('button',{name:'Select Budew'}))
 expect(screen.getByLabelText('Research context')).toHaveTextContent('Context: Active Deck › Budew')
 expect(screen.getByRole('textbox')).toHaveValue('')
 await type('Unsubmitted Budew question')
 fireEvent.click(screen.getByRole('button',{name:'Select Risky Ruins'}))
 expect(screen.getByLabelText('Research context')).toHaveTextContent('Context: Active Deck › Risky Ruins')
 expect(screen.getByRole('textbox')).toHaveValue('')
 expect(screen.getByRole('article')).toHaveTextContent('Captured deck fact.')
 fireEvent.click(screen.getByRole('button',{name:'Clear selected card'}))
 expect(screen.getByLabelText('Research context')).toHaveTextContent('Context: Active Deck')
 expect(screen.queryByRole('button',{name:'Clear selected card'})).not.toBeInTheDocument()
 expect(calls(fetch)).toHaveLength(1)
})

test('selected card Ask sends exact printing and finish once; new context remains marked on pending result',async()=>{
 let release!:(value:unknown)=>void
 const fetch=setup(()=>new Promise(r=>release=r))
 fireEvent.click(screen.getByRole('button',{name:'Select Budew'}))
 await screen.findByText('Context: Active Deck › Budew')
 await type("What's the point of running Budew in this deck?")
 const ask=screen.getByRole('button',{name:'Ask'});fireEvent.click(ask);fireEvent.click(ask)
 expect(calls(fetch)).toHaveLength(1)
 expect(JSON.parse(calls(fetch)[0][1]!.body as string)).toMatchObject({scope:'selected_card_research',printing:'budew-1',variant:'holo',revision:157})
 fireEvent.click(screen.getByRole('button',{name:'Select Risky Ruins'}))
 release(answer);await screen.findByRole('article')
 expect(screen.getByText(/Submitted: Active Deck › Budew/)).toBeInTheDocument()
 expect(screen.getByText(/This result belongs to the submitted snapshot/)).toBeInTheDocument()
 expect(calls(fetch)).toHaveLength(1)
})

test.each(['Remove Budew','Change deck'])('%s clears stale selection and draft with no Research submission',async action=>{
 const fetch=setup();await screen.findByText(/Configured: gemini/)
 fireEvent.click(screen.getByRole('button',{name:'Select Budew'}));await type()
 fireEvent.click(screen.getByRole('button',{name:action}))
 await waitFor(()=>expect(screen.queryByRole('button',{name:'Clear selected card'})).not.toBeInTheDocument())
 expect(screen.getByRole('textbox')).toHaveValue('')
 expect(calls(fetch)).toHaveLength(0)
})

test('deck failure retains bounded diagnostics and no raw output',async()=>{
 const fetch=setup(async()=>({status:'invalid_answer_contract',answer:null,contract_diagnostics:{condition:'json_syntax',json_parsed:false,raw:'PRIVATE'}}))
 await type();fireEvent.click(screen.getByRole('button',{name:'Ask'}));await screen.findByRole('alert')
 fireEvent.click(screen.getByText('Validation details'))
 expect(screen.getByLabelText('Validation details')).toHaveTextContent('JSON parsing failed.')
 expect(within(screen.getByRole('complementary')).queryByText('PRIVATE')).not.toBeInTheDocument()
 expect(calls(fetch)).toHaveLength(1)
})

test('deck packet citations and captured source metadata are inspectable without another call',async()=>{
 const fetch=setup(async()=>({...answer,snapshot:{as_of:'2026-09-27',eligible_lists:159,self_comparison:'unavailable',packet_bytes:13556,packet_hash:'packet-hash',source_reference_count:159,
  source_reference_sample:[{id:'ref-list',source:'limitless-main',resource:'list',url:'https://limitlesstcg.com/decks/list/1',content_hash:'source-hash'}]},
  envelope:{content_hash:'envelope-hash',omitted:[],active_deck:{id:'active-deck',name:'Captured Deck',revision:157,references:['ref-deck']},packet:{
   evidence:[{id:'ev-comparison',kind:'comparison',classification:'EMPIRICAL_EVIDENCE',fields:[{field:'eligible_lists',value:'159'}],references:[]}],
   references:[{id:'ref-deck',source:'PokéLab workspace',resource:'revision/157',content_hash:'deck-hash'}],coverage:{omitted:['cap/mechanics:2'],unavailable:['creator_intent']}}}}))
 await type();fireEvent.click(screen.getByRole('button',{name:'Ask'}));await screen.findByRole('article')
 fireEvent.click(screen.getByText('Evidence coverage and snapshot'))
 expect(screen.getByText(/As of 2026-09-27/)).toBeVisible()
 expect(screen.getByText('packet-hash')).toBeVisible()
 fireEvent.click(screen.getByText('Population source sample (1 of 159)'))
 expect(screen.getByRole('link',{name:'Open source list'})).toHaveAttribute('href','https://limitlesstcg.com/decks/list/1')
 fireEvent.click(screen.getByRole('button',{name:'comparison'}))
 expect(screen.getByRole('region',{name:'Inspected evidence'})).toHaveTextContent('159')
 fireEvent.click(screen.getByRole('button',{name:'Inspect evidence active-deck'}))
 expect(screen.getByRole('region',{name:'Inspected evidence'})).toHaveTextContent('Captured Deck')
 expect(calls(fetch)).toHaveLength(1)
})
