import {test,expect} from '@playwright/test'

test('card-pool rejection exposes recovered safe reason without prose or retry',async({page})=>{
 let calls=0
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url())
  if(!['127.0.0.1','localhost'].includes(url.hostname))return route.abort()
  if(url.pathname==='/api/v1/agent/status')return route.fulfill({json:{version:'pokelab-research-v1',available:true,provider:'gemini',model:'mock-only'}})
  if(url.pathname==='/api/v1/agent/research'){
   calls++
   return route.fulfill({json:{status:'invalid_answer_contract',answer:null,contract_diagnostics:{condition:'uncited_limitation_claim',json_parsed:true,schema_valid:true}}})
  }
  if(url.pathname.startsWith('/api/'))return route.fulfill({status:503,json:{}})
  return route.continue()
 })
 await page.goto('/')
 const agent=page.getByRole('complementary',{name:'PokéLab Agent'})
 if(await agent.getByRole('button',{name:'Toggle Agent panel'}).getAttribute('aria-expanded')==='false')await agent.getByRole('button',{name:'Toggle Agent panel'}).click()
 await agent.getByLabel('Research area').selectOption('pool')
 await agent.getByRole('textbox').fill('What cards can mill my opponent?')
 await agent.getByRole('button',{name:'Ask',exact:true}).click()
 await expect(agent.getByRole('alert')).toBeVisible()
 await agent.getByText('Validation details',{exact:true}).click()
 await expect(agent.getByLabel('Validation details')).toContainText('uncited_limitation_claim')
 await expect(agent.getByLabel('Validation details')).toContainText('A factual claim was placed in uncited limitations.')
 await expect(agent.getByRole('article')).toHaveCount(0)
 expect(calls).toBe(1)
})

for(const width of [1440,900])test(`open card-pool panel with no deck at ${width}px`,async({page},info)=>{
 let calls=0,artCalls=0
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url())
  if(!['127.0.0.1','localhost'].includes(url.hostname))return route.abort()
  if(url.pathname==='/api/v1/agent/status')return route.fulfill({json:{version:'pokelab-research-v1',available:true,provider:'gemini',model:'mock-only'}})
  if(url.pathname==='/api/v1/deck-workspace')return route.fulfill({status:503,json:{detail:'No deck for open research fixture'}})
  if(url.pathname==='/api/v1/cards/coal-1'){
   artCalls++;return route.fulfill({json:{card:{id:'coal-1',image_url:'/fixture-art.svg'}}})
  }
  if(url.pathname==='/fixture-art.svg')return route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="350" height="490"><rect width="350" height="490" fill="#243449"/><text x="28" y="80" fill="white" font-size="28">Coalossal</text><text x="28" y="130" fill="white" font-size="18">Mock artwork for UI QA</text></svg>'})
  if(url.pathname==='/api/v1/agent/research'){
   calls++;expect(route.request().postDataJSON()).toMatchObject({scope:'card_pool_research',include_deck:false,revision:null})
   return route.fulfill({json:{status:'answered',answer:{outcome:'answered',facts:[{text:"I'd start by researching Coalossal for its direct discard effect rather than assuming tournament success.",evidence:['ev-pool-fixture']}],interpretation:[],limitations:['Tournament success is not established.']},envelope:{content_hash:'fixture',active_deck:{},omitted:[],packet:{evidence:[{id:'ev-pool-fixture',kind:'card-pool-candidate',fields:[{field:'name',value:'"Coalossal"'},{field:'printing',value:'"coal-1"'}],references:[]}],references:[],coverage:{omitted:[],unavailable:[]}}}}})
  }
  return route.continue()
 })
 await page.setViewportSize({width,height:1000});await page.goto('/')
 const agent=page.getByRole('complementary',{name:'PokéLab Agent'})
 if(await agent.getByRole('button',{name:'Toggle Agent panel'}).getAttribute('aria-expanded')==='false')await agent.getByRole('button',{name:'Toggle Agent panel'}).click()
 await agent.getByLabel('Research area').selectOption('pool')
 await agent.getByRole('textbox').fill('What cards can mill my opponent?')
 await expect(agent.getByRole('button',{name:'Ask',exact:true})).toBeEnabled()
 expect(calls).toBe(0)
 await agent.getByRole('button',{name:'Ask',exact:true}).click()
 await expect(agent.getByRole('article')).toContainText("I'd start by researching")
 await expect(agent.getByRole('button',{name:'Inspect evidence ev-pool-fixture'})).toBeHidden()
 expect(artCalls).toBe(0)
 await agent.getByRole('button',{name:'Coalossal',exact:true}).hover()
 const preview=page.getByRole('tooltip',{name:'Coalossal card preview'})
 await expect(preview.getByRole('img')).toBeVisible()
 await expect.poll(()=>preview.getByRole('img').evaluate((e:HTMLImageElement)=>e.naturalWidth)).toBe(350)
 const previewBox=await preview.boundingBox();expect(previewBox!.width).toBeGreaterThanOrEqual(350)
 expect(previewBox!.x).toBeGreaterThanOrEqual(0);expect(previewBox!.x+previewBox!.width).toBeLessThanOrEqual(width)
 await page.screenshot({path:info.outputPath(`card-name-preview-${width}.png`)})
 await page.keyboard.press('Escape');await expect(preview).toBeHidden()
 expect(calls).toBe(1);expect(artCalls).toBe(1)
 await agent.getByText('Inspect supporting evidence',{exact:true}).click()
 await agent.getByRole('button',{name:'Inspect evidence ev-pool-fixture'}).click()
 await expect(agent.getByRole('region',{name:'Inspected evidence'})).toBeVisible()
 expect(calls).toBe(1)
 const box=await agent.boundingBox();expect(box!.x+box!.width).toBeLessThanOrEqual(width)
 await agent.screenshot({path:info.outputPath(`card-pool-${width}.png`)})
})
