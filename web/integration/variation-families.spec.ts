import { test, expect, type APIRequestContext } from '@playwright/test'

async function command(request:APIRequestContext,body:object){
 const current=await (await request.get('/api/v1/deck-workspace')).json()
 const response=await request.post('/api/v1/deck-workspace',{data:{...body,schema_version:2,revision:current.revision}})
 expect(response.ok()).toBeTruthy();return response.json()
}

test('real Mega Charizard gold appears in the settled family without changing certified allocation keys',async({page,request},info)=>{
 await command(request,{action:'new',discard:true})
 const ownedBefore=await (await request.get('/api/v1/cards/me02-130/ownership?variant=holo')).json()
 await command(request,{action:'quantity',printing_id:'me02-013',variant:'holo',delta:1,exact:true})
 const saved=await command(request,{action:'save'})
 await page.goto('/deck-builder/cards/me02-013?variant=holo')
 await page.getByRole('button',{name:'Variations',exact:true}).click()
 const gold=page.locator('[data-variation="me02-130:holo"]')
 for(const id of ['me02-013','me02-109','me02-125','me02-130','mep-023','mep-029']){
  await expect(page.locator(`[data-variation="${id}:holo"]`)).toHaveCount(1)
 }
 await gold.scrollIntoViewIfNeeded();await expect(gold).toHaveCSS('border-top-width','1px')
 await expect(gold.locator('.deck-stepper')).toHaveCSS('justify-content','center')
 await expect(gold.getByRole('status')).toHaveText('0')
 await expect(page.getByRole('button',{name:/default printing/i})).toHaveCount(0)
 await gold.getByRole('button',{name:'Add Mega Charizard X ex to deck',exact:true}).click()
 await expect(gold.getByRole('status')).toHaveText('1')
 const selected=await (await request.get('/api/v1/deck-workspace')).json()
 const key=(await (await request.get('/api/v1/cards/me02-130')).json()).card.deck_identity
 expect(selected.deck.entries.find((e:any)=>e.identity===saved.deck.entries[0].identity)).toEqual(saved.deck.entries[0])
 expect(selected.defaults[key]).toMatchObject({printing_id:'me02-130',variant:'holo'})
 expect(await (await request.get('/api/v1/cards/me02-130/ownership?variant=holo')).json()).toEqual(ownedBefore)
 await gold.hover({position:{x:3,y:3}});await page.waitForTimeout(600)
 await expect(page.locator('.competitive-popup')).toHaveCount(0)
 await page.screenshot({path:info.outputPath('mega-charizard-family.png')})
 await page.reload();await page.getByRole('button',{name:'Variations',exact:true}).click()
 await expect(gold.getByRole('status')).toHaveText('1')
 await expect(gold).toHaveCSS('border-top-width','1px')
})

test('Boss historical family has truthful legality and different Charizard gameplay stays outside',async({page,request},info)=>{
 const response=await request.get('/api/v1/cards/me01-114/variations?scope=family&page_size=50')
 const family=await response.json(),ids=new Set(family.cards.map((c:any)=>c.id))
 expect(ids.size).toBe(9)
 expect(family.cards.find((c:any)=>c.id==='swsh9-132').legal.standard).toBe(false)
 expect(family.cards.filter((c:any)=>c.id==='me02.5-183').map((c:any)=>c.ownership.variant).sort()).toEqual(['holo','normal','reverse'])
 await page.goto('/deck-builder/cards/me01-114')
 await page.getByRole('button',{name:'Variations',exact:true}).click()
 const finish=family.cards.find((c:any)=>c.id==='swsh9-132').ownership.variant
 const historical=page.locator(`[data-variation="swsh9-132:${finish}"]`)
 await historical.scrollIntoViewIfNeeded();await expect(historical).toHaveCSS('border-top-width','1px')
 await page.screenshot({path:info.outputPath('boss-historical-family.png')})
 await historical.getByRole('link',{name:`Inspect swsh9-132 ${finish}`,exact:true}).click()
 await expect(page).toHaveURL(new RegExp(`cards/swsh9-132\\?variant=${finish}`))
 await expect(page.getByText('standard: not legal · expanded: legal',{exact:true})).toBeVisible()
 await expect(page.getByRole('button',{name:'Variations',exact:true})).toHaveAttribute('aria-expanded','true')
 await expect(page.locator('[data-variation="me01-114:normal"]')).toHaveCount(1)
 const charizard=await (await request.get('/api/v1/cards/base1-4/variations?scope=family&page_size=50')).json()
 const charIds=charizard.cards.map((c:any)=>c.id)
 expect(charIds).not.toContain('swsh4-25');expect(charIds).not.toContain('swsh10.5-010');expect(charIds).not.toContain('A1-035')
})
