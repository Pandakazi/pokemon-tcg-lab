import {MemoryRouter} from 'react-router'
import {render,screen,fireEvent,waitFor,within} from '@testing-library/react'
import {test,expect,vi} from 'vitest'
import {CompetitiveProvider} from './Competitive'
import {ResearchAgentProvider,ResearchPanel,useResearchAgent} from './ResearchAgent'
import packets from '../../tests/fixtures/card_pool_pm_20261002.json'

function Harness(){
 const agent=useResearchAgent()
 return <><button onClick={()=>agent.select({printing:'budew-1',name:'Budew',variant:'holo',pool:true})}>Reference Budew</button><ResearchPanel open toggle={()=>{}}/></>
}
function setup(result?:unknown){
 const calls:Record<string,unknown>[]=[]
 vi.stubGlobal('fetch',vi.fn(async(url:string,options?:RequestInit)=>{
  if(url==='/api/v1/agent/status')return {ok:true,json:async()=>({version:'pokelab-research-v1',available:true,provider:'gemini',model:'explicit-model'})}
  if(url==='/api/v1/agent/research'){
   calls.push(JSON.parse(options!.body as string))
   if(result)return {ok:true,json:async()=>result}
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
 expect(screen.getByRole('button',{name:'Inspect evidence ev-pool-test',hidden:true})).not.toBeVisible()
 fireEvent.click(screen.getByText('Inspect supporting evidence'))
 fireEvent.click(screen.getByRole('button',{name:'Inspect evidence ev-pool-test'}))
 expect(screen.getByRole('region',{name:'Inspected evidence'})).toBeVisible()
 expect(screen.getByText(/no deck context/)).toBeVisible()
 expect(calls).toHaveLength(1)
})

test.each([true,false])('v2 renders all trusted cards after optional degradation; synthesis=%s',async(keepSynthesis)=>{
 const evidence=packets.simple.packet.evidence
 const cards=evidence.map(e=>{
  const f=Object.fromEntries(e.fields.map(field=>[field.field,JSON.parse(field.value)]))
  return {evidence_id:e.id,name:f.name,printing:f.printing,standard:f.standard,components:f.components.map((c:{component:string;name:string;text:string;structured:{cost?:string[];damage?:number}})=>({kind:c.component,name:c.name,text:c.text,cost:c.structured.cost??null,damage:c.structured.damage??null}))}
 })
 const calls=setup({status:'answered',answer:{version:'pokelab-card-pool-answer-v2',outcome:'answered',facts:[],card_facts:cards,
  interpretation:keepSynthesis?[{text:'The printed discard quantities help compare the mechanical output.',evidence:[cards[0].evidence_id]}]:[],
  limitations:['Tournament strength is not established.']},envelope:packets.simple,
  synthesis_diagnostics:{omitted:[{field:'synthesis',index:1,condition:'unsupported_numeric_card_claim'}]}})
 await screen.findByText(/Configured:/)
 fireEvent.change(screen.getByLabelText('Research area'),{target:{value:'pool'}})
 fireEvent.change(screen.getByRole('textbox'),{target:{value:'What cards can mill my opponent?'}})
 fireEvent.click(screen.getByRole('button',{name:'Ask'}));await screen.findByRole('article')
 const printed=within(screen.getByRole('region',{name:'Printed card facts'}))
 for(const card of cards)expect(printed.getByRole('button',{name:card.name})).toBeVisible()
 expect(printed.getByText('Printed damage: 150')).toBeVisible()
 expect(printed.getByText('Energy: Fighting · Colorless · Colorless · Colorless')).toBeVisible()
 expect(printed.queryByText('Printed damage: 0')).toBeNull()
 expect(screen.getByRole('article')).not.toHaveTextContent('999 HP')
 expect(screen.getByRole('article')).not.toHaveTextContent('DIRECT_MECHANICAL')
 if(keepSynthesis)expect(screen.getAllByText('The printed discard quantities help compare the mechanical output.')[0].compareDocumentPosition(screen.getByRole('region',{name:'Printed card facts'}))&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
 fireEvent.click(printed.getByRole('button',{name:'Centiskorch'}))
 expect(screen.getByRole('region',{name:'Inspected evidence'})).toBeVisible()
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
