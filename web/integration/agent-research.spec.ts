import {test,expect,type APIRequestContext,type Page} from './fixtures'

async function prepare(request:APIRequestContext) {
 let workspace=await (await request.get('/api/v1/deck-workspace')).json()
 workspace=await (await request.post('/api/v1/deck-workspace',{data:{action:'new',discard:true,schema_version:2,revision:workspace.revision}})).json()
 const pool=await (await request.get('/api/v1/cards?category=Pokemon&page_size=2')).json(),card=pool.cards[0]
 const added=await request.post('/api/v1/deck-workspace',{data:{action:'quantity',delta:1,printing_id:card.id,variant:card.ownership.variant,schema_version:2,revision:workspace.revision}})
 expect(added.ok()).toBeTruthy()
 return card
}

async function available(page:Page) {
 await page.route('**/api/v1/agent/status',route=>route.fulfill({json:{available:true,provider:'gemini',model:'fixture-only'}}))
}

for(const width of [1440,900])test(`selected card/deck context to fixture answer and inspectable sources at ${width}px`,async({page,request},info)=>{
 const card=await prepare(request)
 const before=await (await request.get('/api/v1/deck-workspace')).json()
 const ownership=await (await request.get(`/api/v1/cards/${card.id}/ownership`)).json()
 const detail=await (await request.get(`/api/v1/cards/${card.id}`)).json()
 await available(page)
 let calls=0
 await page.route('**/api/v1/agent/research',route=>{
  calls++;expect(route.request().postDataJSON()).toMatchObject({scope:'conversation',printing:card.id,include_deck:true,revision:before.revision})
  return route.fulfill({json:{status:'answered',conversation_id:'a'.repeat(32),answer:{paragraphs:[{text:`${card.name} is the selected card. A plausible interpretation is a supporting role.`,evidence:['card-fixture']}],facts:[]},envelope:{content_hash:'fixture',selected:{printing:card.id},revision:before.revision,window:'30',as_of:'2026-10-11',proof_requested:false,omissions:[],evidence:[{id:'card-fixture',kind:'fact',title:card.name,printing:card.id,source:'TCGdex',value:{printing:card.id,attacks:detail.card.attacks||[]}}]}}})
 })
 await page.setViewportSize({width,height:1000})
 await page.goto(`/deck-builder/cards/${card.id}`)
 await page.getByRole('button',{name:'Ask about this card',exact:true}).click()
 const agent=page.getByRole('complementary',{name:'PokéLab Agent'})
 await expect(agent).toContainText(card.name)
 await agent.getByRole('checkbox',{name:/Use active deck/}).check()
 await agent.getByRole('textbox',{name:'Ask PokéLab'}).fill('What is the point of running this card in my deck?')
 await agent.getByRole('button',{name:'Ask',exact:true}).click()
 await expect(agent.getByRole('article',{name:'Agent answer'})).toContainText('plausible interpretation')
 await expect(agent.getByRole('region',{name:'Sources and card facts'})).toHaveCount(0)
 await agent.getByRole('button',{name:'Inspect support for paragraph 1'}).click()
 await expect(agent.getByRole('region',{name:'Sources and card facts'})).toContainText(card.id)
 await agent.screenshot({path:info.outputPath(`conversation-${width}.png`)})
 const box=await agent.boundingBox();expect(box!.width).toBeGreaterThan(300);expect(box!.x+box!.width).toBeLessThanOrEqual(width)
 expect(await (await request.get('/api/v1/deck-workspace')).json()).toEqual(before)
 expect(await (await request.get(`/api/v1/cards/${card.id}/ownership`)).json()).toEqual(ownership)
 expect(calls).toBe(1)
 await agent.getByRole('button',{name:'Toggle Agent panel'}).click()
 await page.locator('.detail-art').getByRole('button',{name:`Add ${card.name} to deck`,exact:true}).click()
 await page.getByRole('button',{name:'Toggle Agent panel'}).click()
 await expect(agent).toContainText('current context has changed')
})

test('truncation and provider failure never render partial answers or retry',async({page,request})=>{
 const card=await prepare(request);await available(page)
 let calls=0
 await page.route('**/api/v1/agent/research',route=>{
  calls++;return route.fulfill({json:{status:calls===1?'output_token_limit_reached':'provider_failure',answer:null}})
 })
 await page.goto(`/deck-builder/cards/${card.id}`)
 await page.getByRole('button',{name:'Ask about this card',exact:true}).click()
 const agent=page.getByRole('complementary',{name:'PokéLab Agent'})
 await agent.getByRole('textbox').fill('fixture:truncated')
 await agent.getByRole('button',{name:'Ask',exact:true}).click()
 await expect(agent.getByRole('alert')).toContainText('No partial answer')
 await expect(agent.getByRole('article')).toHaveCount(0);expect(calls).toBe(1)
 await agent.getByRole('textbox').fill('fixture:http429')
 await agent.getByRole('button',{name:'Ask',exact:true}).click()
 await expect(agent.getByRole('alert').last()).toContainText('No automatic retry')
 await expect(agent.getByRole('article')).toHaveCount(0);expect(calls).toBe(2)
})
