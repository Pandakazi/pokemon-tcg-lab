import { test, expect, type APIRequestContext } from '@playwright/test'

async function command(request:APIRequestContext,body:object){
 const current=await (await request.get('/api/v1/deck-workspace')).json()
 const response=await request.post('/api/v1/deck-workspace',{data:{...body,schema_version:2,revision:current.revision}})
 expect(response.ok()).toBeTruthy();return response.json()
}
test.beforeEach(async({request})=>{await command(request,{action:'new',discard:true})})

for(const builder of [false,true])for(const list of [false,true]){
 test(`artwork-only 500ms hover, cancellation and grace: builder=${builder}, list=${list}`,async({page})=>{
  // Known local pixels isolate pointer/timer assertions from CDN availability.
  await page.route('https://assets.tcgdex.net/**',route=>route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="700"><rect width="500" height="700" fill="#a78bfa"/></svg>'}))
  await page.goto(`${builder?'/deck-builder':'/'}?category=Trainer&q=Ultra+Ball`)
  if(list)await page.getByRole('button',{name:'List',exact:true}).click()
  const tile=page.locator('[data-printing-id]').first(),art=tile.locator('.card-art img'),popup=page.locator('.competitive-popup')
  await expect(art).toBeVisible()
  await page.clock.install();await page.clock.pauseAt(new Date(Date.now()+1000))
  for(const selector of ['.card-link>strong','.printing','code','small',builder?'.deck-ownership':'.ownership-controls',builder?'.deck-stepper output':'.quantity-row output','button']){
   await tile.locator(selector).first().hover();await page.clock.runFor(600);await expect(popup).toHaveCount(0)
  }
  // Blank bottom corner of the article is outside image and controls.
  const box=(await tile.boundingBox())!;await page.mouse.move(box.x+box.width-1,box.y+box.height-1)
  await page.clock.runFor(600);await expect(popup).toHaveCount(0)
  await art.hover();await page.clock.runFor(400);await page.mouse.move(1,1);await page.clock.runFor(600);await expect(popup).toHaveCount(0)
  await art.hover();await page.clock.runFor(499);await expect(popup).toHaveCount(0)
  await page.clock.runFor(1);await expect(popup).toBeVisible()
  if(builder)await expect(popup.locator('strong').filter({hasText:'0 Cards in deck'})).toHaveCount(1)
  else await expect(popup).not.toContainText('Cards in deck')
  await popup.hover();await page.clock.runFor(200);await expect(popup).toBeVisible()
  await page.mouse.move(1,1);await page.clock.runFor(179);await expect(popup).toBeVisible()
  await page.clock.runFor(1);await expect(popup).toHaveCount(0)
 })
}

test('real variation allocations, defaults, aggregate tooltip and reload persistence',async({page,request},info)=>{
 test.setTimeout(120000)
 const card=(await (await request.get('/api/v1/cards?category=Trainer&q=Ultra+Ball')).json()).cards[0]
 const variants=(await (await request.get(`/api/v1/cards/${card.id}/variations?scope=deck`)).json()).cards
 const a=variants[0],b=variants.find((v:any)=>v.id!==a.id||v.ownership.variant!==a.ownership.variant)
 expect(b).toBeTruthy()
 const detail=`/deck-builder/cards/${card.id}`
 await page.goto(detail);await page.getByRole('button',{name:'Variations',exact:true}).click()
 const first=page.locator(`[data-variation="${a.id}:${a.ownership.variant}"]`),second=page.locator(`[data-variation="${b.id}:${b.ownership.variant}"]`)
 await first.getByRole('button',{name:`Add ${a.name} to deck`,exact:true}).click()
 await second.getByRole('button',{name:`Add ${b.name} to deck`,exact:true}).click({clickCount:2,delay:80})
 await expect(first.getByRole('status')).toHaveText('1');await expect(second.getByRole('status')).toHaveText('2')
 await expect(first).toContainText('Total in deck: 3');await expect(second).toContainText('Total in deck: 3')
 await second.getByRole('button',{name:'Set as default printing',exact:true}).click()
 await expect(second.getByRole('button',{name:'✓ Default printing',exact:true})).toBeVisible()
 const tray=page.getByRole('complementary',{name:'Active deck'})
 await tray.getByRole('button',{name:'Save',exact:true}).click();await expect(tray.locator('footer')).toContainText('Saved')
 const saved=await (await request.get('/api/v1/deck-workspace')).json()
 await first.getByRole('button',{name:'Set as default printing',exact:true}).click()
 await expect(first.getByRole('button',{name:'✓ Default printing',exact:true})).toBeVisible()
 expect((await (await request.get('/api/v1/deck-workspace')).json()).deck.entries).toEqual(saved.deck.entries)
 await page.reload();await page.getByRole('button',{name:'Variations',exact:true}).click()
 await expect(first.getByRole('status')).toHaveText('1');await expect(second.getByRole('status')).toHaveText('2')
 await expect(first.getByRole('button',{name:'✓ Default printing',exact:true})).toBeVisible()
 await first.scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('mixed-printing-allocations.png')})
 for(const width of [1440,1280,1100]){
  await page.setViewportSize({width,height:1000})
  await first.scrollIntoViewIfNeeded()
  const geometry=await page.locator('.deck-variation-grid>.variation-card').evaluateAll(cards=>cards.slice(0,4).map(card=>{
   const frame=card.getBoundingClientRect(),art=card.querySelector('.artwork-frame')!.getBoundingClientRect()
   const buttons=card.querySelectorAll('.deck-stepper button'),left=buttons[0].getBoundingClientRect(),right=buttons[1].getBoundingClientRect()
   const preference=card.querySelector(':scope>button')!.getBoundingClientRect()
   return {x:frame.x,y:frame.y,width:frame.width,height:frame.height,border:getComputedStyle(card).borderTopWidth,center:frame.x+frame.width/2,artCenter:art.x+art.width/2,controlCenter:(left.x+right.right)/2,contained:preference.left>=frame.left&&preference.right<=frame.right&&preference.bottom<frame.bottom}
  }))
  for(const card of geometry){
   expect(card.border).toBe('1px');expect(card.contained).toBeTruthy()
   expect(Math.abs(card.center-card.artCenter)).toBeLessThan(1)
   expect(Math.abs(card.center-card.controlCenter)).toBeLessThan(1)
   expect(Math.abs(card.width-geometry[0].width)).toBeLessThan(1)
   if(Math.abs(card.y-geometry[0].y)<1)expect(Math.abs(card.height-geometry[0].height)).toBeLessThan(1)
  }
  expect(await page.locator('.deck-variation-grid').evaluate(el=>el.scrollWidth<=el.clientWidth)).toBeTruthy()
  await expect(first.getByRole('status')).toHaveText('1');await expect(second.getByRole('status')).toHaveText('2')
  await expect(page.locator('.variation-card').nth(2).getByRole('status')).toHaveText('0')
  await expect(first).toContainText('Total in deck: 3')
  await first.hover({position:{x:3,y:3}});await page.waitForTimeout(600)
  await expect(page.locator('.competitive-popup')).toHaveCount(0)
  await page.screenshot({path:info.outputPath(`framed-variations-${width}.png`)})
 }
 await page.goto('/deck-builder?category=Trainer&q=Ultra+Ball')
 const tile=page.locator(`[data-printing-id="${card.id}"]`)
 await tile.locator('.card-art img').hover()
 await expect(page.locator('.competitive-popup strong').filter({hasText:'3 Cards in deck'})).toBeVisible()
 await page.mouse.move(1,1)
 await tile.getByRole('button',{name:`Add ${card.name} to deck`,exact:true}).click()
 await expect(tile.getByRole('status')).toHaveText('4')
 const updated=await (await request.get('/api/v1/deck-workspace')).json()
 expect(updated.deck.entries[0].allocations.find((v:any)=>v.printing_id===a.id&&v.variant===a.ownership.variant).quantity).toBe(2)
 await tile.locator('.card-art img').hover()
 await expect(page.locator('.competitive-popup strong').filter({hasText:'4 Cards in deck'})).toBeVisible()
})

test('detail artwork independent of deck membership and view; controls centered; honest fallback',async({page,request},info)=>{
 test.setTimeout(120000)
 const cards=(await (await request.get('/api/v1/cards?category=Pokemon&stages=Basic&page_size=24')).json()).cards.slice(0,3)
 await command(request,{action:'quantity',printing_id:cards[0].id,delta:1})
 for(const [index,card] of cards.entries()){
  if(index===0)await page.goto('/deck-builder?stages=Basic')
  if(index===1){await page.goto('/deck-builder?stages=Basic');await page.getByRole('button',{name:'List',exact:true}).click()}
  // Direct navigation also verifies detail requires no preceding Library render.
  await page.goto(`/deck-builder/cards/${card.id}`)
  const image=page.locator('.detail-art .card-art img')
  await expect.poll(()=>image.evaluateAll(imgs=>imgs.some(i=>(i as HTMLImageElement).naturalWidth>0)),{timeout:45000}).toBeTruthy()
  const controls=page.locator('.detail-art .deck-card-controls'),buttons=controls.locator('.deck-stepper')
  expect(await buttons.evaluate(el=>getComputedStyle(el).justifyContent)).toBe('center')
  const parent=(await controls.boundingBox())!,left=(await buttons.locator('button').first().boundingBox())!,right=(await buttons.locator('button').last().boundingBox())!
  expect(Math.abs((left.x+right.x+right.width)/2-(parent.x+parent.width/2))).toBeLessThan(2)
  await image.hover();await page.waitForTimeout(650);await expect(page.locator('.competitive-popup')).toHaveCount(0)
  await page.getByRole('button',{name:/^Enlarge /}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.keyboard.press('Escape')
 }
 await page.screenshot({path:info.outputPath('centered-detail-artwork.png')})
 // A failed high-resolution asset tries the same printing's low resolution once.
 await page.route('https://assets.tcgdex.net/**/high.webp',route=>route.abort())
 await page.reload()
 await expect.poll(()=>page.locator('.detail-art .card-art img').evaluateAll(imgs=>imgs.some(i=>(i as HTMLImageElement).naturalWidth>0)),{timeout:45000}).toBeTruthy()
 await expect(page.locator('.detail-art .card-art img')).toHaveAttribute('src',/low\.webp$/)
 await page.route('https://assets.tcgdex.net/**/low.webp',route=>route.abort())
 await page.reload();await expect(page.locator('.detail-art')).toContainText('Image unavailable')
})
