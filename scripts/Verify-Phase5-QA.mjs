// Read-only verification of the restarted PM QA runtime; never edits user decks.
import { createRequire } from 'node:module'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import fs from 'node:fs'
import assert from 'node:assert/strict'

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')
const require=createRequire(path.join(root,'web','package.json'))
const {chromium}=require('@playwright/test')
const expected=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim()
const base=process.env.POKELAB_QA_URL||'http://127.0.0.1:5175'
const read=async route=>{const response=await fetch(base+route);assert(response.ok,route);return response.json()}
const before=await read('/api/v1/deck-workspace')
assert.equal(before.schema_version,2)
assert.equal(before.runtime_revision,expected)
const browser=await chromium.launch()
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}})
 const errors=[];page.on('pageerror',error=>errors.push(error.message))
 await page.goto(base+'/deck-builder')
 // Explicitly bypass the frontend cache after restarting both services.
 const session=await page.context().newCDPSession(page)
 await session.send('Network.enable');await session.send('Network.setCacheDisabled',{cacheDisabled:true})
 await session.send('Page.reload',{ignoreCache:true})
 await page.getByRole('complementary',{name:'Active deck'}).getByRole('heading',{name:before.deck.name,exact:true}).waitFor()
 const readBack=await page.evaluate(async()=>await (await fetch('/api/v1/deck-workspace',{cache:'no-store'})).json())
 assert.equal(readBack.runtime_revision,expected)
 const card=(await read('/api/v1/cards?category=Trainer&q=Ultra+Ball')).cards[0]
 await page.goto(base+'/deck-builder?category=Trainer&q=Ultra+Ball')
 const image=page.locator(`[data-printing-id="${card.id}"] .card-art img`)
 await image.waitFor();await image.hover()
 const popup=page.locator('.competitive-popup');await popup.waitFor()
 const count=before.deck.entries.find(e=>e.identity===card.deck_identity)?.quantity||0
 assert((await popup.innerText()).includes(`${count} ${count===1?'Card':'Cards'} in deck`))
 await page.mouse.move(1,1)
 await page.goto(base+`/deck-builder/cards/${card.id}`)
 const art=page.locator('.detail-art .card-art img');await art.waitFor()
 await page.waitForFunction(()=>{const image=document.querySelector('.detail-art .card-art img');return image?.naturalWidth>0},null,{timeout:45000})
 assert.equal(await page.locator('.detail-art .deck-stepper').evaluate(el=>getComputedStyle(el).justifyContent),'center')
 await art.hover();await page.waitForTimeout(650)
 assert.equal(await page.locator('.competitive-popup').count(),0)
 await page.getByRole('button',{name:'Variations',exact:true}).click()
 await page.locator('.variation-card').first().waitFor()
 assert(await page.getByRole('button',{name:/Set as default printing|✓ Default printing/}).count()>0)
 const output=path.join(root,'.cache','manual-qa')
 await page.screenshot({path:path.join(output,'qa-fix1-runtime.png'),fullPage:true})
 const after=await read('/api/v1/deck-workspace')
 assert.deepEqual(after,before)
 assert.deepEqual(errors,[])
 const result={verified_at:new Date().toISOString(),url:base,commit:expected,schema_version:after.schema_version,revision:after.revision,functional_entries:after.deck.entries.length,saved_decks:after.saved.length,hard_refresh:true,artwork_loaded:true,centered_controls:true,hover_context:true,variation_defaults:true,user_state_unchanged:true,browser_errors:errors}
 fs.writeFileSync(path.join(output,'qa-fix1-runtime.json'),JSON.stringify(result,null,2)+'\n')
 console.log(JSON.stringify(result,null,2))
} finally {await browser.close()}
