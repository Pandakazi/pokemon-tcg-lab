import { test, expect, type Locator } from '@playwright/test'

async function loaded(image:Locator){await expect(image).toBeVisible();await expect.poll(()=>image.evaluate((e:HTMLImageElement)=>e.complete&&e.naturalWidth>0)).toBe(true)}

test('real Gumshoos finishes, pointer light, settled frames, reduced motion and navigation',async({page,request},info)=>{
 const before=await (await request.get('/api/v1/deck-workspace')).json()
 await page.goto('/deck-builder/cards/me01-110?variant=normal')
 await page.getByRole('button',{name:'Variations',exact:true}).click()
 const grid=page.locator('.deck-variation-grid')
 await grid.scrollIntoViewIfNeeded()
 const normal=grid.locator('[data-variation="me01-110:normal"]'),reverse=grid.locator('[data-variation="me01-110:reverse"]'),holo=grid.locator('[data-variation="me01-153:holo"]')
 for(const tile of [normal,reverse,holo]){
  await loaded(tile.locator('img'));await expect(tile).toHaveCSS('border-top-width','1px')
  await expect(tile.locator('.deck-stepper')).toHaveCSS('justify-content','center')
 }
 await expect(normal.locator('.finish-light')).toHaveCount(0)
 for(const [tile,finish] of [[reverse,'reverse'],[holo,'holo']] as const){
  await expect(tile.locator('.finish-surface')).toHaveAttribute('data-finish',finish)
  const img=tile.locator('img'),overlay=tile.locator('.finish-light')
  await expect(overlay).toHaveCSS('pointer-events','none');await expect(overlay).toHaveCSS('visibility','visible')
  const imageBox=(await img.boundingBox())!,foilBox=(await overlay.boundingBox())!
  for(const key of ['x','y','width','height'] as const)expect(Math.abs(imageBox[key]-foilBox[key])).toBeLessThan(1)
 }
 expect(await reverse.locator('.finish-light').evaluate(e=>getComputedStyle(e).clipPath)).not.toBe(await holo.locator('.finish-light').evaluate(e=>getComputedStyle(e).clipPath))
 await page.mouse.move(1,1);await grid.screenshot({path:info.outputPath('gumshoos-rest.png')})
 for(const [tile,label] of [[holo,'holo'],[reverse,'reverse']] as const){
  const box=(await tile.locator('img').boundingBox())!,surface=tile.locator('.finish-surface')
  await page.mouse.move(box.x+box.width*.2,box.y+box.height*.3)
  await expect(surface).toHaveAttribute('data-lit','true')
  expect(await surface.evaluate(e=>parseFloat((e as HTMLElement).style.getPropertyValue('--foil-x')))).toBeCloseTo(20,0)
  await page.mouse.move(box.x+box.width*.8,box.y+box.height*.2,{steps:12})
  expect(await surface.evaluate(e=>parseFloat((e as HTMLElement).style.getPropertyValue('--foil-x')))).toBeCloseTo(80,0)
  await page.waitForTimeout(200);await grid.screenshot({path:info.outputPath(`gumshoos-${label}-pointer.png`)})
  await page.mouse.move(1,1);await expect(surface).not.toHaveAttribute('data-lit')
  await expect.poll(()=>surface.evaluate(e=>getComputedStyle(e).getPropertyValue('--foil-x').trim())).toBe('50%')
 }
 await reverse.hover({position:{x:3,y:3}});await page.waitForTimeout(600)
 await expect(page.locator('.competitive-popup')).toHaveCount(0);await expect(reverse.locator('.finish-surface')).not.toHaveAttribute('data-lit')
 await page.emulateMedia({reducedMotion:'reduce'})
 await reverse.locator('img').hover();await expect(reverse.locator('.finish-surface')).not.toHaveAttribute('data-lit')
 await expect(reverse.locator('.finish-surface')).toHaveCSS('transition-duration','0s')
 await grid.screenshot({path:info.outputPath('gumshoos-reduced-motion.png')})
 await page.emulateMedia({reducedMotion:'no-preference'})
 await reverse.getByRole('link').click();await expect(page).toHaveURL(/me01-110\?variant=reverse/)
 await loaded(page.locator('.detail-art img'))
 await page.getByRole('button',{name:/Enlarge Gumshoos/}).click()
 const dialog=page.getByRole('dialog');await loaded(dialog.locator('img.enlarged-art'))
 await expect(dialog.locator('.finish-surface')).toHaveAttribute('data-finish','reverse')
 await dialog.screenshot({path:info.outputPath('gumshoos-enlarged-reverse.png')})
 await dialog.getByRole('button',{name:/Close/}).click()
 const after=await (await request.get('/api/v1/deck-workspace')).json();expect(after).toEqual(before)
})

test('foil remains static on touch and aligns after resizing with many visible cards',async({page},info)=>{
 await page.goto('/deck-builder/cards/me01-114?variant=reverse')
 await page.getByRole('button',{name:'Variations',exact:true}).click()
 const grid=page.locator('.deck-variation-grid');await grid.scrollIntoViewIfNeeded()
 await expect.poll(()=>grid.locator('.finish-surface').count()).toBeGreaterThan(5)
 for(const width of [1440,1280,1100]){
  await page.setViewportSize({width,height:1000})
  const tile=grid.locator('[data-variation="me01-114:reverse"]'),img=tile.locator('img')
  await loaded(img)
  await expect.poll(async()=>Math.abs((await img.boundingBox())!.width-(await tile.locator('.finish-light').boundingBox())!.width)).toBeLessThan(1)
  await expect(tile).toHaveCSS('border-top-width','1px')
 }
 const image=grid.locator('img').first()
 await image.dispatchEvent('pointermove',{pointerType:'touch',clientX:100,clientY:200})
 await expect(grid.locator('[data-lit]')).toHaveCount(0)
 expect(await page.evaluate(()=>document.getAnimations().length)).toBe(0)
 await grid.screenshot({path:info.outputPath('many-finishes-responsive.png')})
})

test('dark and bright artwork stays readable through Holo and Reverse lighting',async({page},info)=>{
 for(const [id,variant,label] of [['svp-110','holo','dark-holo'],['sv08.5-161','holo','dark-full-art'],['me01-110','reverse','bright-reverse']]){
  await page.goto(`/deck-builder/cards/${id}?variant=${variant}`)
  const art=page.locator('.detail-art img');await loaded(art);await art.hover({position:{x:70,y:120}})
  await page.waitForTimeout(200)
  await page.locator('.detail-art').screenshot({path:info.outputPath(`${label}.png`)})
 }
})

test('a touch device retains static finish distinctions without gestures',async({browser},info)=>{
 const context=await browser.newContext({baseURL:'http://127.0.0.1:5174',hasTouch:true,isMobile:true,viewport:{width:1100,height:1000}})
 try{
  const page=await context.newPage()
  await page.goto('/deck-builder/cards/me01-110?variant=reverse')
  await page.getByRole('button',{name:'Variations',exact:true}).click()
  const grid=page.locator('.deck-variation-grid');await grid.scrollIntoViewIfNeeded()
  expect(await page.evaluate(()=>matchMedia('(hover: none)').matches)).toBe(true)
  for(const finish of ['reverse','holo']){
   const surface=grid.locator(`[data-finish="${finish}"]`)
   await loaded(surface.locator('img'));await surface.locator('img').dispatchEvent('pointermove',{pointerType:'touch',clientX:100,clientY:100})
   await expect(surface).not.toHaveAttribute('data-lit');await expect(surface.locator('.finish-light')).toHaveCSS('visibility','visible')
  }
  await grid.screenshot({path:info.outputPath('gumshoos-touch.png')})
 }finally{await context.close()}
})
