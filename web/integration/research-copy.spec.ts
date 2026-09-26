import { test, expect, type APIRequestContext } from '@playwright/test'

async function current(request:APIRequestContext){return (await request.get('/api/v1/deck-workspace')).json()}
async function command(request:APIRequestContext,body:object){const before=await current(request);const r=await request.post('/api/v1/deck-workspace',{data:{...body,schema_version:2,revision:before.revision}});expect(r.ok()).toBeTruthy();return r.json()}
const archetype='780e0eca3a75532945bfca1e'
test.beforeEach(async({request})=>{await command(request,{action:'new',discard:true})})

for(const kind of ['tournament','composite'] as const)test(`${kind} copy opens a new saved editable 60-card deck and survives reload`,async({page,request},info)=>{
 test.setTimeout(120000)
 const old=await command(request,{action:'save'})
 const root=`/api/v1/research/archetypes/${archetype}`
 const evidence=await(await request.get(root+'/decks')).json()
 const route=kind==='tournament'?`/tournament-decks/${evidence.decks[0].id}`:`/archetypes/${archetype}?window=30`
 const sourceURL=kind==='tournament'?`/api/v1/research/tournament-decks/${evidence.decks[0].id}`:root+'/composite'
 const source=await(await request.get(sourceURL)).json()
 const anchor=source.cards.find((c:any)=>c.card?.id)
 const ownershipURL=`/api/v1/cards/${anchor.card.id}/ownership`
 const ownership=await(await request.get(ownershipURL)).json()
 await page.goto(route)
 const button=page.getByRole('button',{name:kind==='tournament'?'Copy to Deck Builder':'Copy Composite to Deck Builder',exact:true})
 await expect(button).toBeEnabled()
 await page.screenshot({path:info.outputPath(`${kind}-copy-action.png`)})
 await button.click()
 await expect(page).toHaveURL('/deck-builder')
 const tray=page.getByRole('complementary',{name:'Active deck'})
 await expect(tray).toContainText('60 / 60')
 const copied=await current(request)
 expect(copied.deck.id).not.toBe(old.deck.id)
 expect(copied.deck.has_saved).toBe(true)
 expect(copied.saved).toContainEqual(old.saved.find((d:any)=>d.id===old.deck.id))
 const expected:Record<string,number>={}
 for(const c of source.cards)expected[c.card.deck_identity]=(expected[c.card.deck_identity]||0)+c.quantity
 expect(Object.fromEntries(copied.deck.entries.map((e:any)=>[e.identity,e.quantity]))).toEqual(expected)
 await page.reload();await expect(tray).toContainText('60 / 60')
 expect((await current(request)).deck).toEqual(copied.deck)
 await tray.getByRole('button',{name:/Decrease .* in tray/}).first().click()
 await expect(tray).toContainText('59 / 60')
 expect(await(await request.get(sourceURL)).json()).toEqual(source)
 expect(await(await request.get(ownershipURL)).json()).toEqual(ownership)
 await page.screenshot({path:info.outputPath(`${kind}-editable-deck.png`)})
})

test('dirty draft cancellation, server failure and confirmation preserve safe transitions',async({page,request})=>{
 await command(request,{action:'rename',name:'Unsaved draft to preserve'})
 const before=await current(request)
 await page.goto(`/deck-builder/archetypes/${archetype}?window=30`)
 const copy=page.getByRole('button',{name:'Copy Composite to Deck Builder'})
 await expect(copy).toBeEnabled()
 page.once('dialog',d=>d.dismiss());await copy.click()
 expect(await current(request)).toEqual(before)
 await page.route('**/api/v1/deck-workspace/copy-research',r=>r.fulfill({status:503,json:{detail:'Copy unavailable; retry after reload.'}}))
 page.once('dialog',d=>d.accept());await copy.click()
 await expect(page.getByRole('alert')).toContainText('Copy unavailable')
 await expect(page).toHaveURL(/archetypes/)
 expect(await current(request)).toEqual(before)
 await page.unroute('**/api/v1/deck-workspace/copy-research')
 page.once('dialog',d=>d.accept());await copy.click()
 await expect(page).toHaveURL('/deck-builder')
 expect((await current(request)).validation.total).toBe(60)
})

test('unavailable composite disables copy',async({page})=>{
 await page.goto(`/archetypes/${archetype}?window=format`)
 await expect(page.getByRole('button',{name:'Copy Composite to Deck Builder'})).toBeDisabled()
})
