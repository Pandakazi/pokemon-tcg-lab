import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'

test.beforeEach(async({page})=>{
 // All browser assets remain local; backend acceptance server independently
 // blocks outbound connections. No importer or provider is called here.
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url())
  if(!['127.0.0.1','localhost'].includes(url.hostname)) {
   if(route.request().resourceType()==='image')return route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="245" height="342"><rect width="245" height="342" fill="#29405c"/></svg>'})
   return route.abort()
  }
  await route.continue()
 })
})

test('explicit sync states and disabled Analytics tooltip settle in the real shell',async({page})=>{
 let posts=0
 await page.route('**/api/v1/competitive/sync',async route=>{
  const post=route.request().method()==='POST';if(post)posts++
  await route.fulfill({json:post?{status:'complete',last_successful_at:new Date().toISOString(),available_at:new Date(Date.now()+3600000).toISOString()}:{status:'ready',last_successful_at:new Date(Date.now()-18*60000-5000).toISOString()}})
 })
 await page.goto('/')
 await expect(page.getByText(/Competitive data · synced 18m ago/)).toBeVisible()
 const button=page.getByRole('button',{name:'Sync Competitive Data'})
 await button.click()
 await expect(page.getByText(/Competitive data · synced just now/)).toBeVisible()
 await expect(button).toBeDisabled();expect(posts).toBe(1)
 await expect(page.getByText(/Available again in 60m/)).toBeVisible()
 const analytics=page.getByRole('button',{name:'Analytics',exact:true})
 await expect(analytics).toBeDisabled()
 await expect(analytics.locator('..')).toHaveAttribute('title','Coming soon!')
 await page.screenshot({path:'../.cache/preview-sync.png',fullPage:true})
})

test('illustrator detail opens the full exact-printing catalog and clearing restores Library',async({page,request})=>{
 const name='Mitsuhiro Arita',query=new URLSearchParams({illustrators:name})
 const response=await request.get(`/api/v1/cards?${query}&page_size=24&include_image=true`)
 expect(response.status(),await response.text()).toBe(200)
 const source=await response.json()
 expect(source.total).toBeGreaterThan(1)
 const card=source.cards[0]
 await page.goto(`/cards/${card.id}`)
 const artist=page.getByRole('link',{name,exact:true})
 await expect(artist).toHaveAttribute('href',`/?${query}`)
 await artist.click()
 await expect(page.getByText('TCGdex · local SQLite · Illustrator catalog · all indexed printings')).toBeVisible()
 const m=page.locator('.filter-panel details').filter({has:page.locator('summary',{hasText:/^M$/})})
 await expect(m).toHaveAttribute('open','')
 const before=page.url()
 await m.locator('summary').click();await expect(m).not.toHaveAttribute('open','')
 expect(page.url()).toBe(before)
 await m.locator('summary').click();await expect(m.getByRole('checkbox',{name,exact:true})).toBeChecked()
 await expect(page.locator('article[data-printing-id]')).toHaveCount(source.cards.length)
 expect(await page.locator('article[data-printing-id]').evaluateAll(els=>els.map(e=>e.getAttribute('data-printing-id')))).toEqual(source.cards.map((c:any)=>c.id))
 await page.screenshot({path:'../.cache/preview-illustrator.png',fullPage:true})
 await page.getByRole('button',{name:'Clear filters',exact:true}).click()
 await expect(page.getByText('TCGdex · local SQLite · Standard Pokémon')).toBeVisible()
 await expect(page.locator('article[data-printing-id]').first()).toBeVisible()
})

test('Collection artist discovery includes unowned printings and clearing restores owned collection',async({page,request})=>{
 const query=new URLSearchParams({illustrators:'Mitsuhiro Arita'})
 const source=await (await request.get(`/api/v1/cards?${query}&page_size=24`)).json()
 await page.goto(`/collection?${query}`)
 await expect(page.getByRole('heading',{name:'Illustrator catalog',exact:true})).toBeVisible()
 await expect(page.locator('article[data-printing-id]')).toHaveCount(source.cards.length)
 expect(await page.locator('article[data-printing-id]').evaluateAll(els=>els.map(e=>e.getAttribute('data-printing-id')))).toEqual(source.cards.map((c:any)=>c.id))
 await page.getByRole('button',{name:'Clear illustrator',exact:true}).click()
 await expect(page.getByRole('heading',{name:'Collection',exact:true})).toBeVisible()
 await expect(page.getByText('No owned variations match. Add cards from the Library or Card Detail.')).toBeVisible()
})

test('generated deck Copy translates local metadata into the full PTCGL fixture',async({page})=>{
 const fixture=JSON.parse(readFileSync('../tests/fixtures/ptcgl-export.json','utf8'))
 const cards=fixture.rows.map((row:any)=>{const card=fixture.cards.find((c:any)=>c.id===row.printing_id);return {...row,canonical_name:card.name,category:card.category}})
 await page.addInitScript(()=>Object.defineProperty(navigator,'clipboard',{value:{writeText:async(text:string)=>{(window as any).copiedDeck=text}}}))
 await page.route('**/api/v1/agent/status',route=>route.fulfill({json:{available:true,provider:'fake',model:'fake'}}))
 await page.route('**/api/v1/agent/research',route=>route.fulfill({json:{status:'answered',answer:{paragraphs:[],facts:[],proposal:{status:'PROPOSED',lifecycle:'FINALIZE',kind:'list',name:'Fixture',source_revision:null,validation_status:'VALIDATED',legality_status:'LEGAL',total_cards:60,category_subtotals:{Pokemon:20,Trainer:32,Energy:8},cards,adds:[],removes:[],unresolved:[],hard_validation:[],strategic_diagnostics:[],repair_notes:[],alternatives:[],premises:[]}}}}))
 await page.goto('/')
 await page.getByRole('textbox',{name:'Ask PokéLab'}).fill('Show the fixture deck.')
 await page.getByRole('button',{name:'Ask',exact:true}).click()
 await page.getByRole('button',{name:'Copy Deck List',exact:true}).click()
 await expect(page.getByText('Copied',{exact:true})).toBeVisible()
 expect(await page.evaluate(()=>(window as any).copiedDeck)).toBe(fixture.expected)
})
