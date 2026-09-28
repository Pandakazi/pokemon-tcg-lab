import {MemoryRouter} from 'react-router'
import {render,screen,fireEvent,waitFor} from '@testing-library/react'
import {test,expect,vi} from 'vitest'
import {CompetitiveProvider} from './Competitive'
import {ResearchAgentProvider,ResearchPanel,useResearchAgent} from './ResearchAgent'

function Harness(){
 const agent=useResearchAgent()
 return <><button onClick={()=>agent.select({printing:'budew-1',name:'Budew',variant:'holo',pool:true})}>Reference Budew</button><ResearchPanel open toggle={()=>{}}/></>
}
function setup(){
 const calls:Record<string,unknown>[]=[]
 vi.stubGlobal('fetch',vi.fn(async(url:string,options?:RequestInit)=>{
  if(url==='/api/v1/agent/status')return {ok:true,json:async()=>({version:'pokelab-research-v1',available:true,provider:'gemini',model:'explicit-model'})}
  if(url==='/api/v1/agent/research'){
   calls.push(JSON.parse(options!.body as string))
   return {ok:true,json:async()=>({status:'answered',answer:{outcome:'answered',facts:[{text:"I'd start by exploring this printed effect.",evidence:['ev-pool-test']}],interpretation:[],limitations:['Tournament success is not established.']},envelope:{content_hash:'fixture',active_deck:{},omitted:[],packet:{evidence:[{id:'ev-pool-test',kind:'card-pool-candidate',fields:[],references:[]}],references:[],coverage:{omitted:[],unavailable:[]}}}})}
  }
  throw new Error('Unexpected request')
 }))
 render(<MemoryRouter><CompetitiveProvider><ResearchAgentProvider><Harness/></ResearchAgentProvider></CompetitiveProvider></MemoryRouter>)
 return calls
}
test('open card-pool Ask works without any DeckProvider; citations and no auto calls',async()=>{
 const calls=setup()
 await screen.findByText(/Configured:/)
 fireEvent.change(screen.getByLabelText('Research area'),{target:{value:'pool'}})
 fireEvent.change(screen.getByRole('textbox'),{target:{value:'What cards can mill my opponent?'}})
 await waitFor(()=>expect(screen.getByRole('button',{name:'Ask'})).toBeEnabled())
 expect(calls).toHaveLength(0)
 fireEvent.click(screen.getByRole('button',{name:'Ask'}))
 await screen.findByRole('article')
 expect(calls).toEqual([{scope:'card_pool_research',question:'What cards can mill my opponent?',revision:null,window:'30',include_deck:false}])
 fireEvent.click(screen.getByRole('button',{name:'Inspect evidence ev-pool-test'}))
 expect(screen.getByRole('region',{name:'Inspected evidence'})).toBeVisible()
 expect(screen.getByText(/no deck context/)).toBeVisible()
 expect(calls).toHaveLength(1)
})
test('reference remains optional and clearing it stays in card-pool mode',async()=>{
 const calls=setup();await screen.findByText(/Configured:/)
 fireEvent.click(screen.getByRole('button',{name:'Reference Budew'}))
 expect(screen.getByText('Context: Standard card pool › Budew')).toBeVisible()
 fireEvent.change(screen.getByRole('textbox'),{target:{value:'Is there another card that stops players from using Tools?'}})
 fireEvent.click(screen.getByRole('button',{name:'Ask'}));await screen.findByRole('article')
 expect(calls[0]).toMatchObject({scope:'card_pool_research',printing:'budew-1',variant:'holo',include_deck:false})
 fireEvent.click(screen.getByRole('button',{name:'Clear selected card'}))
 expect(screen.getByLabelText('Research area')).toHaveValue('pool')
 expect(screen.getByText(/This result belongs to the submitted snapshot/)).toBeVisible()
 expect(calls).toHaveLength(1)
})
