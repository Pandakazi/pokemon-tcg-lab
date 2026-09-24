import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import path from 'node:path'

test('approved gallery → API → synchronized SQLite, with real images and no upstream data requests',async ({page,request})=>{
 const root=path.resolve('..')
 const python=process.env.POKELAB_TEST_PYTHON || path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python')
 const sql=`import os,sqlite3,json
from pokelab.engine import functional_signature
c=sqlite3.connect('file:'+os.getenv('TCG_CARDS_DB_PATH','data/cards.sqlite3')+'?mode=ro',uri=True)
groups={}
for raw,release in c.execute("SELECT c.raw,COALESCE(json_extract(s.raw,'$.releaseDate'),'') FROM cards c LEFT JOIN sets s ON s.id=c.set_id WHERE c.standard=1 AND c.game='tcg' AND c.category='Pokemon'"):
 card=json.loads(raw)
 key=functional_signature(card)
 rank=(release,card.get('regulationMark',''),card['id'])
 if key not in groups or rank>groups[key][0]: groups[key]=(rank,card)
print(json.dumps(sorted([v[1] for v in groups.values()],key=lambda card:card['id'])[:48]))`
 const expected=JSON.parse(execFileSync(python,['-c',sql],{cwd:root,encoding:'utf8'}))
 expect(expected.length).toBe(48)
 const upstream:string[]=[]
 await page.route('https://api.tcgdex.net/**',route=>{upstream.push(route.request().url());return route.abort()})
 const status=await request.get('/api/v1/status'); expect(status.ok()).toBeTruthy()
 await page.goto('/')
 const tiles=page.locator('article[data-printing-id]')
 await expect(tiles).toHaveCount(24)
 for(let n=0;n<24;n++){
  await expect(tiles.nth(n)).toHaveAttribute('data-printing-id',expected[n].id)
  await expect(tiles.nth(n)).toContainText(expected[n].name)
  await expect(tiles.nth(n)).toContainText(`${expected[n].set.name} · ${expected[n].localId}`)
 }
 await expect.poll(()=>page.locator('.card-art img').evaluateAll(imgs=>imgs.filter(i=>(i as HTMLImageElement).naturalWidth>0).length),{timeout:45000}).toBeGreaterThan(0)
 await page.screenshot({path:'test-results/gallery-real-data.png',fullPage:true})
 await page.getByRole('button',{name:'Next',exact:true}).click()
 await expect(tiles.first()).toHaveAttribute('data-printing-id',expected[24].id)
 await page.getByRole('button',{name:'Previous',exact:true}).click()
 await expect(tiles.first()).toHaveAttribute('data-printing-id',expected[0].id)
 expect(upstream).toEqual([])
})
