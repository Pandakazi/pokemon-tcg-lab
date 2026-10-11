import {MemoryRouter} from 'react-router'
import {render,screen,fireEvent,waitFor,within} from '@testing-library/react'
import {test,expect,vi} from 'vitest'
import {Application} from './App'
import {CompetitiveProvider} from './Competitive'

test('artifact is category-ordered and copies exact resolved list with lightweight confirmation',async()=>{
 const rows=[{card_id:'e',category:'Energy',printing_id:'energy-1',canonical_name:'Fire Energy',quantity:9},{card_id:'t',category:'Trainer',printing_id:'trainer-1',canonical_name:'Ultra Ball',quantity:32},{card_id:'p',category:'Pokemon',printing_id:'poke-1',canonical_name:'Dragapult ex',quantity:19}]
 const proposal={status:'PROPOSED',lifecycle:'FINALIZE',kind:'list',name:'Fixture',source_revision:null,validation_status:'VALIDATED',legality_status:'LEGAL',total_cards:60,category_subtotals:{Energy:9,Trainer:32,Pokemon:19},cards:rows,adds:[],removes:[],unresolved:[],hard_validation:[],strategic_diagnostics:[],repair_notes:[],alternatives:[],premises:[]}
 const writeText=vi.fn().mockResolvedValue(undefined)
 Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText}})
 const {agent,calls}=setup(async()=>({...result,answer:{...result.answer,proposal}}))
 await ask('Show that deck.');const region=await agent.findByRole('region',{name:'Proposed deck review'})
 const items=within(region).getAllByRole('listitem').map(row=>row.textContent)
 expect(items[0]).toContain('Dragapult ex');expect(items[1]).toContain('Ultra Ball');expect(items[2]).toContain('Fire Energy')
 expect(within(region).getByLabelText('Calculated category subtotals')).toHaveTextContent('Pokémon: 19 · Trainer: 32 · Energy: 9 · Total: 60')
 fireEvent.click(within(region).getByRole('button',{name:'Copy Deck List'}))
 await within(region).findByText('Copied')
 const copied=writeText.mock.calls[0][0]
 expect(copied).toContain('19 Dragapult ex TWM 130');expect(copied).toContain('32 Ultra Ball SVI 196');expect(copied).toContain('9 Basic {R} Energy SVE 2');expect(copied).toContain('Total Cards: 60')
 expect(copied).not.toContain('poke-1')
 expect(calls).toHaveLength(1);expect(proposal.cards).toEqual(rows)
})

const evidence={id:'card-fixture',kind:'fact',title:'Example Card',printing:'test-1',value:{name:'Example Card',abilities:[{name:'Example Ability',effect:'Exact locally supplied text.'}]},source:'TCGdex'}
const result={status:'answered',conversation_id:'a'.repeat(32),answer:{paragraphs:[{text:'Example Card and Example Ability suggest a flexible concept to test.',evidence:['card-fixture']}],facts:[evidence]},envelope:{content_hash:'fixture',selected:null,revision:null,window:'30',as_of:'2026-10-03',proof_requested:false,evidence:[evidence],omissions:['empirical-tournament-evidence-not-supplied']}}
function setup(reply:()=>Promise<unknown>=async()=>result,exportReply?:{ok:boolean;status?:number;body:unknown}){
 const calls:Record<string,unknown>[]=[]
 const fetch=vi.fn(async(url:string,options?:RequestInit)=>{
  if(url==='/api/v1/agent/status')return {ok:true,json:async()=>({available:true,provider:'gemini',model:'fake'})}
  if(url==='/api/v1/agent/research'){calls.push(JSON.parse(options!.body as string));return {ok:true,json:reply}}
  if(url==='/api/v1/decks/export-ptcgl')return {ok:exportReply?.ok??true,status:exportReply?.status,json:async()=>exportReply?.body??({text:'Pokémon: 1\n19 Dragapult ex TWM 130\n\nTrainer: 1\n32 Ultra Ball SVI 196\n\nEnergy: 1\n9 Basic {R} Energy SVE 2\n\nTotal Cards: 60',warnings:[]})}
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

test('unmapped printing blocks the clipboard without another Agent request',async()=>{
 const proposal={status:'PROPOSED',lifecycle:'FINALIZE',kind:'list',name:'Fixture',source_revision:null,validation_status:'VALIDATED',legality_status:'LEGAL',total_cards:60,cards:[{printing_id:'unsupported-1',canonical_name:'Unknown printing',quantity:60,category:'Pokemon'}],adds:[],removes:[],unresolved:[],hard_validation:[],strategic_diagnostics:[],repair_notes:[],alternatives:[],premises:[]}
 const writeText=vi.fn();Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText}})
 const {agent,calls}=setup(async()=>({...result,answer:{...result.answer,proposal}}),{ok:false,status:422,body:{detail:'The exact printing has no supported local PTCGL set-code/collector mapping.'}})
 await ask();fireEvent.click(await agent.findByRole('button',{name:'Copy Deck List'}))
 await agent.findByText('The exact printing has no supported local PTCGL set-code/collector mapping.')
 expect(writeText).not.toHaveBeenCalled();expect(calls).toHaveLength(1)
})

test('export-only Basic Energy substitution is disclosed beside Copied',async()=>{
 const proposal={status:'PROPOSED',lifecycle:'FINALIZE',kind:'list',name:'Fixture',source_revision:null,validation_status:'VALIDATED',legality_status:'LEGAL',total_cards:60,cards:[{printing_id:'tk-bw-z-3',canonical_name:'Darkness Energy',quantity:60,category:'Energy'}],adds:[],removes:[],unresolved:[],hard_validation:[],strategic_diagnostics:[],repair_notes:[],alternatives:[],premises:[]}
 const writeText=vi.fn().mockResolvedValue(undefined);Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText}})
 const warning='Darkness Energy: copied SVE 7 as an equivalent Basic Energy. PokéLab allocations are unchanged.'
 const {agent,calls}=setup(async()=>({...result,answer:{...result.answer,proposal}}),{ok:true,body:{text:'Pokémon: 0\n\nTrainer: 0\n\nEnergy: 1\n60 Basic {D} Energy SVE 7\n\nTotal Cards: 60',warnings:[warning]}})
 await ask();fireEvent.click(await agent.findByRole('button',{name:'Copy Deck List'}))
 await agent.findByText('Copied');expect(agent.getByText(warning)).toBeVisible()
 expect(writeText.mock.calls[0][0]).not.toContain('tk-bw-z-3');expect(calls).toHaveLength(1)
 expect(proposal.cards[0].printing_id).toBe('tk-bw-z-3')
})

test('default conversational UI needs no deck or taxonomy and sends one explicit call',async()=>{
 const {calls,agent}=setup()
 expect(agent.queryByLabelText('Research area')).toBeNull()
 await ask();await agent.findByRole('article',{name:'Agent answer'})
 expect(calls).toHaveLength(1);expect(calls[0]).toMatchObject({scope:'conversation',include_deck:false})
 expect(agent.queryByRole('region',{name:'Sources and card facts'})).toBeNull()
 expect(agent.queryByText(/Evidence underneath|Coverage boundaries|Validation scope|Printed facts/)).toBeNull()
 fireEvent.click(agent.getByRole('button',{name:'Show sources'}))
 expect(agent.getByRole('region',{name:'Sources and card facts'})).toBeVisible()
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
 const artworkCalls=()=>fetch.mock.calls.filter(([url])=>String(url).startsWith('/api/v1/cards/test-1')).length
 const baseline=artworkCalls()
 fireEvent.pointerEnter(agent.getByRole('button',{name:'Example Ability'}))
 expect(await screen.findByRole('tooltip',{name:'Example Ability printed text'})).toHaveTextContent('Exact locally supplied text.')
 expect(artworkCalls()).toBe(baseline);expect(calls).toHaveLength(1)
 fireEvent.click(agent.getByRole('button',{name:'Example Ability'}))
 expect(agent.getByRole('region',{name:'Sources and card facts'})).toBeVisible()
})

test('proof opens existing evidence and keeps inference distinct',async()=>{
 const {agent}=setup(async()=>({...result,envelope:{...result.envelope,proof_requested:true}}))
 await ask('Prove it.');await agent.findByRole('article')
 expect(agent.getByRole('region',{name:'Sources and card facts'})).toBeVisible()
 expect(agent.getByText(/Recommendations are judgment/)).toBeVisible()
})

test.each(['Build me a Pikachu deck','Explain this custom deck','Critique this deck','What exact changes would you make?'])('ordinary custom request %s keeps cited evidence on demand',async question=>{
 const {agent}=setup(async()=>({...result,answer:{...result.answer,facts:[{...evidence,kind:'evidence'}],notices:['printed_fact_review','empirical_claim_unverified']}}))
 await ask(question);await agent.findByRole('article')
 expect(agent.queryByRole('region',{name:'Sources and card facts'})).toBeNull()
 fireEvent.click(agent.getByRole('button',{name:'Show sources'}))
 expect(agent.getByRole('region',{name:'Sources and card facts'})).toBeVisible()
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

test('invalid proposal stays visible with separate construction and advisory review, no write actions',async()=>{
 const proposal={status:'PROPOSED',lifecycle:'FINALIZE',kind:'list',name:'Experimental',source_revision:158,
  validation_status:'NEEDS_REPAIR',legality_status:'INVALID',total_cards:60,cards:[{card_id:'x',printing_id:'test-1',canonical_name:'Example Card',quantity:4}],
  adds:[],removes:[],unresolved:[],hard_validation:['Two ACE SPEC cards are not allowed.'],
  strategic_diagnostics:['Review the Energy package.'],repair_notes:['Keep the core and replace the conflicting support slot.'],alternatives:[],premises:[],limitations:['Cached legality, not tournament certification.']}
 const {calls,agent}=setup(async()=>({...result,answer:{...result.answer,proposal}}))
 await ask('Give me the finished 60.');await agent.findByRole('region',{name:'Proposed deck review'})
 expect(agent.queryByText('Two ACE SPEC cards are not allowed.')).toBeNull()
 expect(agent.queryByText('Validation scope')).toBeNull()
 fireEvent.click(agent.getByRole('button',{name:'Review deck details'}))
 expect(agent.getByText('Two ACE SPEC cards are not allowed.')).toBeVisible()
 expect(agent.getByText('Review the Energy package.')).toBeVisible()
 expect(agent.getByText(/nothing has been applied or saved/)).toBeVisible()
 expect(agent.getByText(/Needs repair before use/)).toBeVisible()
 expect(agent.queryByRole('button',{name:/Apply|Save deck/})).toBeNull()
 expect(agent.getByRole('article')).toHaveTextContent('suggest a flexible concept')
 expect(calls).toHaveLength(1)
})

test('role alternatives reuse the existing card preview without changing proposal layout or submitting again',async()=>{
 const proposal={status:'PROPOSED',lifecycle:'DRAFT',kind:'list',name:'Concept',source_revision:null,validation_status:'NEEDS_REPAIR',legality_status:'UNKNOWN',total_cards:0,cards:[],adds:[],removes:[],unresolved:[],hard_validation:[],strategic_diagnostics:[],repair_notes:[],premises:[],alternatives:[{role:'draw support',candidates:[{canonical_name:'Alternative Card',printing_id:'test-1'}]}]}
 const {calls,agent}=setup(async()=>({...result,answer:{...result.answer,proposal}}))
 await ask();await agent.findByRole('region',{name:'Proposed deck review'})
 fireEvent.click(agent.getByRole('button',{name:'Review deck details'}))
 fireEvent.click(agent.getByText('Role-preserving alternatives'))
 fireEvent.pointerEnter(agent.getByRole('button',{name:'Alternative Card'}))
 const tooltip=await screen.findByRole('tooltip',{name:'Alternative Card card preview'})
 expect(tooltip).toHaveStyle({width:'350px'})
 expect(within(tooltip).getByRole('img')).toHaveAttribute('src','/local-art.webp')
 expect(calls).toHaveLength(1)
})

test('generated artifact renders trusted subtotals and an incomplete total without model labels',async()=>{
 const proposal={status:'PROPOSED',lifecycle:'FINALIZE',kind:'list',name:'Generated concept',source_revision:null,validation_status:'NEEDS_REPAIR',legality_status:'INCOMPLETE',total_cards:59,category_subtotals:{Pokemon:18,Trainer:31,Energy:10},cards:[{card_id:'x',printing_id:'test-1',canonical_name:'Example Card',quantity:4}],adds:[],removes:[],unresolved:[],hard_validation:['Deck must contain exactly 60 cards.'],strategic_diagnostics:[],repair_notes:[],alternatives:[],premises:[]}
 const {calls,agent}=setup(async()=>({...result,answer:{paragraphs:[],facts:[],proposal,historical_snapshot:true,artifact_id:'artifact-fixture'}}))
 await ask('Recount that deck.');await agent.findByRole('region',{name:'Proposed deck review'})
 expect(agent.getByLabelText('Calculated category subtotals')).toHaveTextContent('Trainer: 31')
 expect(agent.getByLabelText('Calculated category subtotals')).toHaveTextContent('Total: 59')
 expect(agent.getByText(/Previously proposed artifact/)).toBeVisible()
 expect(agent.getByText(/Needs repair before use/)).toBeVisible()
 expect(agent.queryByText(/Trainer \(32\)/)).toBeNull()
 expect(calls).toHaveLength(1)
})

test('factual and missing-artifact notices remain separate from natural prose',async()=>{
 const {agent}=setup(async()=>({...result,answer:{paragraphs:[{text:'I would preserve the core.',evidence:[]}],facts:[evidence],notices:['printed_fact_review','missing_artifact']}}))
 await ask();await agent.findByRole('article')
 expect(agent.getByText('I would preserve the core.')).toBeVisible()
 expect(agent.getByText(/That card detail needs a closer look/)).toBeVisible()
 expect(agent.getByText(/No structured list or changes were supplied/)).toBeVisible()
 expect(agent.queryByText(/I cannot verify the exact printed details/)).toBeNull()
})
