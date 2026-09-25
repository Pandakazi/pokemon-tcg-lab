// Read-only verification against the freshly restarted persistent PM QA runtime.
import { createRequire } from 'node:module'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import fs from 'node:fs'
import crypto from 'node:crypto'
import assert from 'node:assert/strict'
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')
const require=createRequire(path.join(root,'web/package.json'))
const {chromium,expect}=require('@playwright/test')
const expected=execFileSync('git',['-c',`safe.directory=${root.replaceAll('\\','/')}`,'rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim()
const base=process.env.POKELAB_QA_URL||'http://127.0.0.1:5175'
const read=async route=>{const r=await fetch(base+route);assert(r.ok,route);return r.json()}
const before=await read('/api/v1/deck-workspace')
assert.equal(before.runtime_revision,expected);assert.equal(before.schema_version,2)
const card=(await read('/api/v1/cards?category=Trainer&q=Ultra+Ball')).cards[0]
const stats=await read(`/api/v1/competitive/cards/${card.id}`)
const archetype=stats.archetypes.find(a=>a.id==='/decks/284')
assert(archetype)
const route=`/api/v1/research/archetypes/${archetype.research_id}`
const [summary,core,composite,evidence]=await Promise.all([read(route),read(route+'/cards'),read(route+'/composite'),read(route+'/decks')])
assert.equal(summary.eligible_decks,archetype.eligible_decks)
assert.equal(composite.status,'available');assert.equal(composite.total,60)
assert.equal(composite.cards.reduce((n,c)=>n+c.quantity,0),60)
const browser=await chromium.launch()
const output=path.join(root,'.cache/manual-qa')
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}})
 const errors=[];page.on('pageerror',e=>errors.push(e.message))
 await page.goto(`${base}/deck-builder/archetypes/${archetype.research_id}?window=30`)
 const session=await page.context().newCDPSession(page)
 await session.send('Network.enable');await session.send('Network.setCacheDisabled',{cacheDisabled:true})
 await session.send('Page.reload',{ignoreCache:true})
 await expect(page.getByRole('heading',{name:archetype.name,exact:true})).toBeVisible()
 await expect(page.getByRole('region',{name:'Archetype Composite'}).getByText('60 cards',{exact:true})).toBeVisible()
 await expect(page.getByRole('complementary',{name:'Active deck'}).getByRole('heading',{name:before.deck.name,exact:true})).toBeVisible()
 await page.waitForFunction(()=>[...document.querySelectorAll('.research-cards img')].slice(0,5).every(i=>i.naturalWidth>0))
 await page.screenshot({path:path.join(output,'phase6-archetype.png')})
 await page.getByRole('region',{name:'Tournament decks'}).locator('.evidence-list a').first().click()
 await expect(page.getByRole('heading',{name:'Tournament Deck Research'})).toBeVisible()
 await expect(page.getByText('60 cards',{exact:true})).toBeVisible()
 await page.screenshot({path:path.join(output,'phase6-tournament.png')})
 await page.setViewportSize({width:900,height:800})
 await expect(page.getByRole('heading',{name:'Tournament Deck Research'})).toBeVisible()
 await page.screenshot({path:path.join(output,'phase6-compact.png')})
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)
 assert.deepEqual(await read('/api/v1/deck-workspace'),before)
 const hashes=JSON.parse(fs.readFileSync(path.join(output,'phase6-before-hashes.json'),'utf8').replace(/^\uFEFF/,''))
 for(const record of hashes) assert.equal(crypto.createHash('sha256').update(fs.readFileSync(record.Path)).digest('hex').toUpperCase(),record.Hash,record.Path)
 assert.deepEqual(errors,[])
 const result={verified_at:new Date().toISOString(),commit:expected,url:base,schema_version:before.schema_version,revision:before.revision,functional_entries:before.deck.entries.length,saved_decks:before.saved.length,hard_refresh:true,eligible_decks:summary.eligible_decks,tournaments:summary.tournament_count,core_cards:core.cards.length,composite_total:composite.total,categories:composite.categories,first_evidence:evidence.decks[0].id,collection_deck_source_hashes_unchanged:true,workspace_unchanged:true,browser_errors:errors}
 fs.writeFileSync(path.join(output,'phase6-runtime.json'),JSON.stringify(result,null,2)+'\n')
 console.log(JSON.stringify(result,null,2))
} finally {await browser.close()}
