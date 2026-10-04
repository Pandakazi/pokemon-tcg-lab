import {test,expect} from '@playwright/test'

for(const width of [1440,900])test(`invalid deck proposal continues conversation without writes at ${width}px`,async({page},info)=>{
 let calls=0,writes=0
 await page.route('**/*',async route=>{
  const req=route.request(),url=new URL(req.url())
  if(!['127.0.0.1','localhost'].includes(url.hostname))return route.abort()
  if(url.pathname==='/api/v1/agent/status')return route.fulfill({json:{available:true,provider:'gemini',model:'mock-only'}})
  if(url.pathname==='/api/v1/agent/research'){
   calls++
   return route.fulfill({json:{status:'answered',answer:{paragraphs:[{text:'The core is still worth exploring; replace the conflicting support role.',evidence:[]}],facts:[],proposal:{status:'PROPOSED',lifecycle:'FINALIZE',kind:'diff',name:'Experimental Pikachu',source_revision:158,validation_status:'NEEDS_REPAIR',legality_status:'INVALID',total_cards:60,
    cards:[{card_id:'f',printing_id:'fixture',canonical_name:'Pikachu ex',quantity:4}],
    removes:[{card_id:'absent',printing_id:'absent',canonical_name:'Absent Card',quantity:2,current_quantity:0,validated:false}],
    adds:[{card_id:'f',printing_id:'fixture',canonical_name:'Pikachu ex',quantity:1,current_quantity:3}],
    unresolved:[],hard_validation:['This exact list contains two ACE SPEC cards.'],strategic_diagnostics:['The Darkness source for the Ability needs review.'],repair_notes:['Keep the concept; select a legal replacement for the recovery role.'],alternatives:[],premises:[],limitations:['Cached supported checks, not tournament certification.']}}}})
  }
  if(url.pathname.startsWith('/api/')&&req.method()!=='GET')writes++
  if(url.pathname.startsWith('/api/'))return route.fulfill({status:503,json:{}})
  return route.continue()
 })
 await page.setViewportSize({width,height:1000});await page.goto('/')
 const agent=page.getByRole('complementary',{name:'PokéLab Agent'})
 await agent.getByRole('textbox').fill('Give me the exact cards and quantities you would change.')
 await agent.getByRole('button',{name:'Ask',exact:true}).click()
 const review=agent.getByRole('region',{name:'Proposed deck review'})
 await expect(review).toContainText('Source revision: 158')
 await expect(review).toContainText('currently 0 · cut not valid')
 await expect(review).toContainText('currently 3')
 await expect(review).toContainText('two ACE SPEC')
 await expect(review).toContainText('Strategic checks — advisory')
 await expect(agent.getByRole('article')).toContainText('still worth exploring')
 await expect(agent.getByRole('button',{name:/Apply|Save deck/})).toHaveCount(0)
 expect(calls).toBe(1);expect(writes).toBe(0)
 const box=await agent.boundingBox();expect(box!.x+box!.width).toBeLessThanOrEqual(width)
 await agent.screenshot({path:info.outputPath(`deck-proposal-${width}.png`)})
})
