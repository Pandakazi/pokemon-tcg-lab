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
 let calls=0
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url())
  if(!['127.0.0.1','localhost'].includes(url.hostname))return route.abort()
  if(url.pathname==='/api/v1/agent/status')return route.fulfill({json:{version:'pokelab-research-v1',available:true,provider:'gemini',model:'mock-only'}})
  if(url.pathname==='/api/v1/deck-workspace')return route.fulfill({status:503,json:{detail:'No deck for open research fixture'}})
  if(url.pathname==='/api/v1/agent/research'){
   calls++;expect(route.request().postDataJSON()).toMatchObject({scope:'card_pool_research',include_deck:false,revision:null})
   return route.fulfill({json:{status:'answered',answer:{outcome:'answered',facts:[{text:"I'd start by researching a direct mill effect rather than assuming tournament success.",evidence:['ev-pool-fixture']}],interpretation:[],limitations:['Tournament success is not established.']},envelope:{content_hash:'fixture',active_deck:{},omitted:[],packet:{evidence:[{id:'ev-pool-fixture',kind:'card-pool-candidate',fields:[],references:[]}],references:[],coverage:{omitted:[],unavailable:[]}}}}})
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
 await agent.getByRole('button',{name:'Inspect evidence ev-pool-fixture'}).click()
 await expect(agent.getByRole('region',{name:'Inspected evidence'})).toBeVisible()
 expect(calls).toBe(1)
 const box=await agent.boundingBox();expect(box!.x+box!.width).toBeLessThanOrEqual(width)
 await agent.screenshot({path:info.outputPath(`card-pool-${width}.png`)})
})
