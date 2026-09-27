import {MemoryRouter} from 'react-router'
import {render,screen,fireEvent,waitFor,within} from '@testing-library/react'
import {test,expect,vi} from 'vitest'
import {Application} from './App'
import {CompetitiveProvider} from './Competitive'

function setup(reply:()=>Promise<unknown>,holdSave?:()=>Promise<void>) {
 const card={id:'test-1',name:'Example Card',deck_identity:'functional-1',category:'Pokemon',localId:'1',set:{id:'test'},legal:{standard:true},legality_provenance:{source:'TCGdex',checked_at:'today'},ownership:{functional_id:'functional-1',library_id:'library-1',variant:'normal',quantity:2,functional_total:2,library_total:2}}
 let revision=7
 const fetch=vi.fn(async(url:string,options?:RequestInit)=>{
  let result:unknown
  if(url==='/api/v1/agent/status')result={version:'pokelab-research-v1',available:true,provider:'gemini',model:'explicit-model',reason:null}
  else if(url==='/api/v1/agent/research')result=await reply()
  else if(url==='/api/v1/deck-workspace'){
   if(options?.method==='POST'){await holdSave?.();revision++}
   result={schema_version:2,defaults:{},revision,deck:{id:'d',name:'Test Deck',dirty:true,entries:[{identity:'functional-1',name:card.name,category:'Pokemon',quantity:1,printing_id:card.id,variant:'normal',presentation_available:true,owned:card.ownership,allocations:[{printing_id:card.id,variant:'normal',quantity:1,available:true,owned:card.ownership}]}]},validation:{state:'IN PROGRESS',total:1,categories:{Pokemon:1},reasons:[],unknown:[],limitations:[]},saved:[]}
  }else if(url.startsWith('/api/v1/cards/test-1?'))result={card,source:'TCGdex',checked_at:'today',fetched_at:'today',game:'tcg'}
  else return {ok:false,status:503,json:async()=>({})}
  return {ok:true,json:async()=>result}
 })
 vi.stubGlobal('fetch',fetch)
 render(<MemoryRouter initialEntries={['/deck-builder/cards/test-1']}><CompetitiveProvider><Application/></CompetitiveProvider></MemoryRouter>)
 return fetch
}
async function select() {
 fireEvent.click(await screen.findByRole('button',{name:'Ask about this card'}))
 const agent=within(screen.getByRole('complementary',{name:'PokéLab Agent'}))
 fireEvent.change(agent.getByRole('textbox'),{target:{value:'What role could this play?'}})
 await waitFor(()=>expect(agent.getByRole('button',{name:'Ask'})).toBeEnabled())
 return agent
}
const answered={status:'answered',answer:{outcome:'answered',facts:[{text:'A supported fact.',evidence:['active-deck']}],interpretation:[],limitations:['Intent is unknown.']}}

test('one request captures acknowledged context and repeated clicks do not queue inference',async()=>{
 let release!:(v:unknown)=>void
 const fetch=setup(()=>new Promise(r=>release=r)),agent=await select()
 const ask=agent.getByRole('button',{name:'Ask'})
 fireEvent.click(ask);fireEvent.click(ask)
 expect(ask).toBeDisabled();expect(agent.getByRole('status')).toHaveTextContent('submitted')
 const requests=fetch.mock.calls.filter(([url])=>url==='/api/v1/agent/research')
 expect(requests).toHaveLength(1)
 expect(JSON.parse(requests[0][1]!.body as string)).toEqual({scope:'selected_card_research',question:'What role could this play?',printing:'test-1',variant:'normal',revision:7,window:'30'})
 release(answered)
 expect(await agent.findByRole('article')).toHaveTextContent('A supported fact')
})

test('pending deck save disables Ask and submission uses the new acknowledged revision',async()=>{
 let release!:()=>void
 const fetch=setup(async()=>answered,()=>new Promise(r=>release=r)),agent=await select()
 fireEvent.click(within(document.querySelector('.detail-art') as HTMLElement).getByRole('button',{name:'Add Example Card to deck'}))
 expect(agent.getByRole('button',{name:'Ask'})).toBeDisabled()
 await waitFor(()=>expect(release).toBeTypeOf('function'));release()
 await waitFor(()=>expect(agent.getByRole('button',{name:'Ask'})).toBeEnabled())
 fireEvent.click(agent.getByRole('button',{name:'Ask'}))
 await agent.findByRole('article')
 expect(JSON.parse(fetch.mock.calls.find(([url])=>url==='/api/v1/agent/research')![1]!.body as string).revision).toBe(8)
})

test.each(['output_token_limit_reached','invalid_answer_contract','internal_assessment_failure','provider_failure'])('%s displays no completed answer and makes no automatic retry',async status=>{
 const fetch=setup(async()=>({status,answer:null})),agent=await select()
 fireEvent.click(agent.getByRole('button',{name:'Ask'}))
 await agent.findByRole('alert')
 expect(agent.queryByRole('article')).not.toBeInTheDocument()
 expect(fetch.mock.calls.filter(([url])=>url==='/api/v1/agent/research')).toHaveLength(1)
})

test.each([
 ['invalid_answer_contract',{condition:'json_syntax',json_parsed:false,schema_valid:false,markdown_fence_prefix:true},'JSON parsing failed.'],
 ['invalid_answer_contract',{condition:'schema_validation',json_parsed:true,schema_valid:false,errors:[{path:['facts','<item>','evidence'],condition:'too_long'}]},'facts → item → evidence: above maximum count.'],
 ['invalid_answer_contract',{condition:'invalid_reference',json_parsed:true,schema_valid:true,unknown_reference_count:2,source_reference_id_count:1},'Source IDs used as citations: 1.'],
 ['internal_assessment_failure',{condition:'internal_assessment_error'},'Internal assessment failed; no model-quality judgment was made.'],
])('exposes bounded %s details without retry',async(status,contract_diagnostics,expected)=>{
 const fetch=setup(async()=>({status,answer:null,contract_diagnostics})),agent=await select()
 fireEvent.click(agent.getByRole('button',{name:'Ask'}));await agent.findByRole('alert')
 fireEvent.click(agent.getByText('Validation details'))
 expect(agent.getByLabelText('Validation details')).toHaveTextContent(expected)
 expect(agent.queryByRole('article')).not.toBeInTheDocument()
 expect(fetch.mock.calls.filter(([url])=>url==='/api/v1/agent/research')).toHaveLength(1)
})

test('diagnostic viewer never renders arbitrary fields, values, paths, messages or raw output',async()=>{
 setup(async()=>({status:'invalid_answer_contract',answer:null,contract_diagnostics:{condition:'PRIVATE_CONDITION',json_parsed:'PRIVATE_BOOL',unknown_reference_count:'PRIVATE_COUNT',message:'PRIVATE_PROVIDER_MESSAGE',raw:'PRIVATE_OUTPUT',reasoning:'PRIVATE_REASONING',errors:Array.from({length:12},()=>({path:['facts','PRIVATE_KEY'],condition:'PRIVATE_ERROR',input:'PRIVATE_INPUT',msg:'PRIVATE_EXCEPTION'}))}}))
 const agent=await select();fireEvent.click(agent.getByRole('button',{name:'Ask'}));await agent.findByRole('alert')
 fireEvent.click(agent.getByText('Validation details'))
 const details=agent.getByLabelText('Validation details')
 expect(details).not.toHaveTextContent('PRIVATE')
 expect(within(details).getAllByRole('listitem')).toHaveLength(8)
 expect(details).toHaveTextContent('facts → unknown field: validation failed.')
})

