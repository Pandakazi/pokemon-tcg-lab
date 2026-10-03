import {MemoryRouter} from 'react-router'
import {render,screen,fireEvent,waitFor,within} from '@testing-library/react'
import {test,expect,vi} from 'vitest'
import {Application} from './App'
import {CompetitiveProvider} from './Competitive'

const evidence={id:'card-fixture',kind:'fact',title:'Example Card',printing:'test-1',value:{name:'Example Card',abilities:[{name:'Example Ability',effect:'Exact locally supplied text.'}]},source:'TCGdex'}
const result={status:'answered',conversation_id:'a'.repeat(32),answer:{paragraphs:[{text:'Example Card and Example Ability suggest a flexible concept to test.',evidence:['card-fixture']}],facts:[evidence]},envelope:{content_hash:'fixture',selected:null,revision:null,window:'30',as_of:'2026-10-03',proof_requested:false,evidence:[evidence],omissions:['empirical-tournament-evidence-not-supplied']}}
function setup(reply:()=>Promise<unknown>=async()=>result){
 const calls:Record<string,unknown>[]=[]
 const fetch=vi.fn(async(url:string,options?:RequestInit)=>{
  if(url==='/api/v1/agent/status')return {ok:true,json:async()=>({available:true,provider:'gemini',model:'fake'})}
  if(url==='/api/v1/agent/research'){calls.push(JSON.parse(options!.body as string));return {ok:true,json:reply}}
  if(url.startsWith('/api/v1/cards/test-1'))return {ok:true,json:async()=>({card:{id:'test-1',image_url:'/local-art.webp'}})}
  return {ok:false,status:503,json:async()=>({})}
 })
 vi.stubGlobal('fetch',fetch)
 render(<MemoryRouter><CompetitiveProvider><Application/></CompetitiveProvider></MemoryRouter>)
 return {calls,fetch,agent:within(screen.getByRole('complementary',{name:'PokéLab Agent'}))}
}
async function ask(question='What directions could this take?'){
 fireEvent.change(screen.getByRole('textbox',{name:'Ask PokéLab'}),{target:{value:question}})
 await waitFor(()=>expect(screen.getByRole('button',{name:'Ask'})).toBeEnabled())
 fireEvent.click(screen.getByRole('button',{name:'Ask'}))
}

test('default conversational UI needs no deck or taxonomy and sends one explicit call',async()=>{
 const {calls,agent}=setup()
 expect(agent.queryByLabelText('Research area')).toBeNull()
 await ask();await agent.findByRole('article',{name:'Agent answer'})
 expect(calls).toHaveLength(1);expect(calls[0]).toMatchObject({scope:'conversation',include_deck:false})
 expect(agent.getByText('Evidence underneath').closest('details')).not.toHaveAttribute('open')
 fireEvent.click(agent.getByRole('button',{name:'Toggle Agent panel'}));fireEvent.click(agent.getByRole('button',{name:'Toggle Agent panel'}))
 expect(calls).toHaveLength(1)
})

test('followups use server session; new conversation resets it without a request',async()=>{
 const {calls,agent}=setup();await ask();await agent.findByRole('article')
 await ask('Which of those is easiest?');await waitFor(()=>expect(agent.getAllByRole('article')).toHaveLength(2))
 expect(calls[1].conversation_id).toBe('a'.repeat(32));expect(calls[1]).not.toHaveProperty('history')
 fireEvent.click(agent.getByRole('button',{name:'New conversation'}));expect(agent.queryByRole('article')).toBeNull()
 expect(calls).toHaveLength(2);await ask('A different concept');await agent.findByRole('article')
 expect(calls[2]).not.toHaveProperty('conversation_id')
})

test('component hover reuses exact printed text without artwork or inference requests',async()=>{
 const {calls,fetch,agent}=setup();await ask();await agent.findByRole('article')
 const baseline=fetch.mock.calls.length
 fireEvent.pointerEnter(agent.getByRole('button',{name:'Example Ability'}))
 expect(await screen.findByRole('tooltip',{name:'Example Ability printed text'})).toHaveTextContent('Exact locally supplied text.')
 expect(fetch.mock.calls).toHaveLength(baseline);expect(calls).toHaveLength(1)
 fireEvent.click(agent.getByRole('button',{name:'Example Ability'}))
 expect(agent.getByText('Evidence underneath').closest('details')).toHaveAttribute('open')
})

test('proof opens existing evidence and keeps inference distinct',async()=>{
 const {agent}=setup(async()=>({...result,envelope:{...result.envelope,proof_requested:true}}))
 await ask('Prove it.');await agent.findByRole('article')
 expect(agent.getByText('Evidence underneath').closest('details')).toHaveAttribute('open')
 expect(agent.getByText(/Inference: the Agent/)).toBeVisible()
})

test.each(['output_token_limit_reached','provider_failure','conversation_expired','internal_assessment_failure'])('failure %s never shows partial answer or retries',async status=>{
 const {calls,agent}=setup(async()=>({status,answer:null}))
 await ask();await agent.findByRole('alert')
 expect(agent.queryByRole('article')).toBeNull();expect(calls).toHaveLength(1)
})

test('single flight disables duplicate submit and new conversation while pending',async()=>{
 let release!:(v:unknown)=>void
 const {calls,agent}=setup(()=>new Promise(resolve=>{release=resolve}))
 await ask();await agent.findByRole('status')
 expect(agent.getByRole('button',{name:'Ask'})).toBeDisabled()
 expect(agent.getByRole('button',{name:'New conversation'})).toBeDisabled()
 fireEvent.submit(agent.getByRole('button',{name:'Ask'}).closest('form')!)
 expect(calls).toHaveLength(1);release(result);await agent.findByRole('article')
})
