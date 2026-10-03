import {test,expect} from '@playwright/test'

// The card-pool resource now appears underneath the default conversation panel.
// Strict research contracts remain covered by backend and ResearchPanel unit tests.
for(const width of [1440,900])test(`conversation, evidence and hover at ${width}px`,async({page},info)=>{
 let calls=0,artCalls=0
 const fact={id:'card-fixture',kind:'fact',title:'Coalossal',printing:'coal-1',value:{name:'Coalossal',attacks:[{name:'Cragalanche',cost:['Fighting','Colorless','Colorless','Colorless'],damage:150,effect:"Discard the top 2 cards of your opponent's deck."}]},source:'TCGdex'}
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url())
  if(!['127.0.0.1','localhost'].includes(url.hostname))return route.abort()
  if(url.pathname==='/api/v1/agent/status')return route.fulfill({json:{version:'pokelab-research-v1',available:true,provider:'gemini',model:'mock-only'}})
  if(url.pathname==='/api/v1/cards/coal-1'){
   artCalls++;return route.fulfill({json:{card:{id:'coal-1',image_url:'/fixture-art.svg'}}})
  }
  if(url.pathname==='/fixture-art.svg')return route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="350" height="490"><rect width="350" height="490" fill="#243449"/><text x="28" y="80" fill="white" font-size="28">Coalossal</text><text x="28" y="130" fill="white" font-size="18">Mock artwork for UI QA</text></svg>'})
  if(url.pathname==='/api/v1/agent/research'){
   calls++;const body=route.request().postDataJSON()
   expect(body).toMatchObject({scope:'conversation',include_deck:false})
   if(calls===2)expect(body.conversation_id).toBe('a'.repeat(32))
   return route.fulfill({json:{status:'answered',conversation_id:'a'.repeat(32),answer:{version:'pokelab-conversation-answer-v1',paragraphs:[{text:'Coalossal gives this concept a concrete starting point. Cragalanche needs setup, so I would test whether the plan survives the prize clock.',evidence:['card-fixture']}],facts:[fact]},envelope:{content_hash:'fixture',revision:null,selected:null,window:'30',as_of:'2026-10-03',proof_requested:calls===2,evidence:[fact],omissions:['empirical-tournament-evidence-not-supplied']}}})
  }
  if(url.pathname.startsWith('/api/'))return route.fulfill({status:503,json:{}})
  return route.continue()
 })
 await page.setViewportSize({width,height:1000});await page.goto('/')
 const agent=page.getByRole('complementary',{name:'PokéLab Agent'})
 await agent.getByRole('textbox').fill('What cards can mill my opponent?')
 await agent.getByRole('button',{name:'Ask',exact:true}).click()
 await expect(agent.getByRole('article')).toContainText('concrete starting point')
 await expect(agent.getByText('Agent status unavailable. Check the API and reload.')).toHaveCount(0)
 expect(calls).toBe(1);expect(artCalls).toBe(0)
 await agent.getByRole('button',{name:'Cragalanche',exact:true}).hover()
 await expect(page.getByRole('tooltip',{name:'Cragalanche printed text'})).toContainText("Discard the top 2 cards of your opponent's deck.")
 expect(artCalls).toBe(0);expect(calls).toBe(1)
 await page.keyboard.press('Escape')
 await agent.getByRole('button',{name:'Coalossal',exact:true}).hover()
 const preview=page.getByRole('tooltip',{name:'Coalossal card preview'})
 await expect(preview.getByRole('img')).toBeVisible()
 await expect.poll(()=>preview.getByRole('img').evaluate((e:HTMLImageElement)=>e.naturalWidth)).toBe(350)
 const box=await preview.boundingBox();expect(box!.x).toBeGreaterThanOrEqual(0);expect(box!.x+box!.width).toBeLessThanOrEqual(width)
 await page.screenshot({path:info.outputPath(`conversation-hover-${width}.png`)})
 await page.keyboard.press('Escape');expect(calls).toBe(1)
 await agent.getByRole('textbox').fill('Prove it. Which parts are facts and which are your reasoning?')
 await agent.getByRole('button',{name:'Ask',exact:true}).click()
 await expect(agent.getByRole('article')).toHaveCount(2)
 await expect(agent.getByText(/Inference: the Agent/).last()).toBeVisible()
 const panel=await agent.boundingBox();expect(panel!.x+panel!.width).toBeLessThanOrEqual(width)
 await agent.screenshot({path:info.outputPath(`conversation-proof-${width}.png`)})
 expect(calls).toBe(2)
})

test('safe contract rejection does not expose output or retry',async({page})=>{
 let calls=0
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url())
  if(!['127.0.0.1','localhost'].includes(url.hostname))return route.abort()
  if(url.pathname==='/api/v1/agent/status')return route.fulfill({json:{available:true,provider:'gemini',model:'mock-only'}})
  if(url.pathname==='/api/v1/agent/research'){calls++;return route.fulfill({json:{status:'invalid_answer_contract',answer:null,contract_diagnostics:{condition:'invalid_reference',json_parsed:true,schema_valid:true}}})}
  if(url.pathname.startsWith('/api/'))return route.fulfill({status:503,json:{}})
  return route.continue()
 })
 await page.goto('/')
 const agent=page.getByRole('complementary',{name:'PokéLab Agent'})
 await agent.getByRole('textbox').fill('Help me compare options')
 await agent.getByRole('button',{name:'Ask',exact:true}).click()
 await expect(agent.getByRole('alert')).toBeVisible()
 await agent.getByText('Validation details',{exact:true}).click()
 await expect(agent.getByLabel('Validation details')).toContainText('invalid_reference')
 await expect(agent.getByRole('article')).toHaveCount(0)
 expect(calls).toBe(1)
})
