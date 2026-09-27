import {test,expect,type APIRequestContext} from '@playwright/test'
test.setTimeout(120000)

async function prepare(request:APIRequestContext) {
 let workspace=await (await request.get('/api/v1/deck-workspace')).json()
 workspace=await (await request.post('/api/v1/deck-workspace',{data:{action:'new',discard:true,schema_version:2,revision:workspace.revision}})).json()
 const pool=await (await request.get('/api/v1/cards?category=Pokemon&page_size=2')).json(),card=pool.cards[0]
 const added=await request.post('/api/v1/deck-workspace',{data:{action:'quantity',delta:1,printing_id:card.id,variant:card.ownership.variant,schema_version:2,revision:workspace.revision}})
 expect(added.ok()).toBeTruthy()
 return card
}

for(const width of [1440,900])test(`real context to fake provider to inspectable answer at ${width}px`,async({page,request},info)=>{
 const card=await prepare(request)
 const before=await (await request.get('/api/v1/deck-workspace')).json()
 const ownership=await (await request.get(`/api/v1/cards/${card.id}/ownership`)).json()
 await page.setViewportSize({width,height:1000})
 await page.goto(`/deck-builder/cards/${card.id}`)
 await page.getByRole('button',{name:'Ask about this card',exact:true}).click()
 const agent=page.getByRole('complementary',{name:'PokéLab Agent'})
 await expect(agent).toContainText(card.name)
 await agent.getByRole('textbox',{name:'Question about this card'}).fill('What is the point of running this card in my deck?')
 await agent.getByRole('button',{name:'Ask',exact:true}).click()
 await expect(agent.getByRole('article',{name:'Research answer'})).toContainText('Plausible interpretation',{timeout:45000})
 await agent.getByRole('button',{name:/Inspect evidence ev-/}).first().click()
 await expect(agent.getByRole('region',{name:'Inspected evidence'})).toContainText(card.id)
 await agent.screenshot({path:info.outputPath(`research-${width}.png`)})
 const box=await agent.boundingBox();expect(box!.width).toBeGreaterThan(300);expect(box!.x+box!.width).toBeLessThanOrEqual(width)
 expect(await (await request.get('/api/v1/deck-workspace')).json()).toEqual(before)
 expect(await (await request.get(`/api/v1/cards/${card.id}/ownership`)).json()).toEqual(ownership)
 await agent.getByRole('button',{name:'Toggle Agent panel'}).click()
 await page.locator('.detail-art').getByRole('button',{name:`Add ${card.name} to deck`,exact:true}).click()
 await page.getByRole('button',{name:'Toggle Agent panel'}).click()
 await expect(agent).toContainText('Current context changed')
})

test('truncation and provider failure never render partial answers or retry',async({page,request})=>{
 const card=await prepare(request)
 let calls=0;page.on('request',r=>{if(r.url().endsWith('/api/v1/agent/research'))calls++})
 await page.goto(`/deck-builder/cards/${card.id}`)
 await page.getByRole('button',{name:'Ask about this card',exact:true}).click()
 const agent=page.getByRole('complementary',{name:'PokéLab Agent'})
 await agent.getByRole('textbox').fill('fixture:truncated')
 await agent.getByRole('button',{name:'Ask',exact:true}).click()
 await expect(agent.getByRole('alert')).toContainText('No partial answer',{timeout:45000})
 await expect(agent.getByRole('article')).toHaveCount(0)
 expect(calls).toBe(1)
 await agent.getByRole('textbox').fill('fixture:http429')
 await agent.getByRole('button',{name:'Ask',exact:true}).click()
 await expect(agent.getByRole('alert')).toContainText('No automatic retry',{timeout:45000})
 await expect(agent.getByRole('article')).toHaveCount(0)
 expect(calls).toBe(2)
})
