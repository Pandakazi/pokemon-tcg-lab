import { test, expect } from '@playwright/test'

test('Library delay, popup crossing, Card Detail research and frozen artwork',async({page,request},testInfo)=>{
 const cards=await (await request.get('/api/v1/cards?category=Trainer&q=Ultra+Ball')).json()
 const card=cards.cards[0]
 const result=await (await request.get(`/api/v1/competitive/cards/${card.id}`)).json()
 expect(result.source).toBe('limitless-main');expect(result.window).toBe('30')
 const sample={...result,status:'observed',format_available:true,format_start:'2026-01-01',sample_size:100,included_decks:20,usage_percent:20,average_copies:3,tournament_count:2,
  top_archetypes:Array.from({length:5},(_,i)=>({id:String(i),name:`Archetype ${i}`,decks:4,eligible_decks:99,share_percent:20,prevalence_percent:null,status:'insufficient_sample'})),
  trend:['7','30','90','format'].map(window=>({window,available:true,points:[{date:'2026-09-20',sample_size:100,included_decks:20,usage_percent:20},{date:'2026-09-23',sample_size:100,included_decks:30,usage_percent:30}]}))}
 sample.archetypes=sample.top_archetypes
 await page.route('**/api/v1/competitive/cards/**',route=>route.fulfill({json:sample}))
 await page.goto('/?category=Trainer&q=Ultra+Ball')
 const tile=page.locator('article').first()
 await expect(tile).toBeVisible()
 await page.clock.install()
 await page.clock.pauseAt(new Date(Date.now()+1000))
 await tile.locator('.card-art').hover();await page.clock.runFor(999)
 await expect(page.getByRole('dialog')).toHaveCount(0)
 await page.clock.runFor(1)
 const popup=page.getByRole('dialog',{name:/competitive preview/})
 await expect(popup).toBeVisible();await expect(popup.getByRole('listitem')).toHaveCount(5)
 await popup.hover();await page.clock.runFor(500);await expect(popup).toBeVisible()
 await page.mouse.move(1,1);await page.clock.runFor(181);await expect(popup).toHaveCount(0)
 await tile.locator('.card-link').click();await expect(page.getByRole('heading',{name:'Competitive research'})).toBeVisible()
 await expect(page.locator('[data-series]')).toHaveCount(4)
 await page.locator('.usage-trend').scrollIntoViewIfNeeded()
 await page.locator('.usage-trend').screenshot({path:testInfo.outputPath('trend.png')})
 await page.getByRole('heading',{name:'Evidence / Dataset'}).scrollIntoViewIfNeeded()
 await expect(page.getByRole('heading',{name:'Evidence / Dataset'})).toBeInViewport()
 await expect(page.getByText('Insufficient sample — 99 decklists')).toHaveCount(5)
 await page.getByRole('group',{name:'Competitive timeframe'}).getByRole('button',{name:'7D',exact:true}).click()
 await expect(page.locator('[data-series]')).toHaveCount(4)
 await page.locator('.detail-art').hover();await page.clock.runFor(1500)
 await expect(page.locator('.competitive-popup')).toHaveCount(0)
 await page.getByRole('button',{name:/^Enlarge /}).click()
 await expect(page.getByRole('dialog')).toBeVisible()
})

test('List hover cancels before one second and card link still navigates',async({page})=>{
 await page.goto('/?category=Trainer&q=Ultra+Ball')
 await page.getByRole('button',{name:'List',exact:true}).click()
 const row=page.locator('.card-row').first();await expect(row).toBeVisible()
 await page.clock.install();await page.clock.pauseAt(new Date(Date.now()+1000));await row.hover();await page.clock.runFor(900)
 await page.mouse.move(1,1);await page.clock.runFor(500)
 await expect(page.locator('.competitive-popup')).toHaveCount(0)
 await row.hover();await page.clock.runFor(1000);await expect(page.locator('.competitive-popup')).toBeVisible()
 await page.mouse.move(1,1);await page.clock.runFor(181)
 await row.locator('.card-link').click();await expect(page).toHaveURL(/\/cards\//)
})
