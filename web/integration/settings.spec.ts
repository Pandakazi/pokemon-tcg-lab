import {test,expect} from './fixtures'

const disconnected={provider:null,connected:false,has_key:false,managed:false,storage:'external'}
const connected={provider:'gemini',connected:true,has_key:true,managed:true,storage:'encrypted'}

test.beforeEach(async({page})=>{
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url())
  if(!['127.0.0.1','localhost'].includes(url.hostname)){
   if(route.request().resourceType()==='image')return route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="245" height="342"><rect width="245" height="342" fill="#29405c"/></svg>'})
   return route.abort()
  }
  return route.continue()
 })
})

test('native Agent Settings modal masks the key, applies one provider, replaces and disconnects',async({page})=>{
 let current=disconnected,posts=0
 await page.route('**/api/v1/agent/status',route=>route.fulfill({json:{version:'pokelab-research-v1',available:current.connected,provider:current.provider,model:null,reason:current.connected?null:'not_configured'}}))
 await page.route('**/api/v1/settings/agent',route=>route.fulfill({json:current}))
 await page.route('**/api/v1/settings/agent/test-apply',async route=>{
  posts++;expect(route.request().postDataJSON()).toEqual({provider:'gemini',api_key:'fixture-browser-key'})
  current=connected as typeof disconnected
  await route.fulfill({contentType:'application/x-ndjson',body:[
   {stage:'validating',message:'Validating API key…'}, {stage:'connecting',message:'Connecting to Gemini…'},
   {stage:'testing',message:'Checking Agent response…'}, {stage:'saving',message:'Saving securely…'},
   {stage:'connected',message:'Gemini connected.',settings:current}].map(event=>JSON.stringify(event)+'\n').join('')})
 })
 await page.route('**/api/v1/settings/agent/disconnect',async route=>{current=disconnected;await route.fulfill({json:{ok:true,settings:current}})})
 await page.goto('/')
 await page.getByRole('button',{name:'Settings',exact:true}).click()
 await page.getByRole('button',{name:'Agent Settings',exact:true}).click()
 const dialog=page.getByRole('dialog',{name:'Agent Settings'})
 await expect(dialog).toBeVisible()
 await expect(dialog.getByText('AI provider: Gemini')).toBeVisible()
 await expect(dialog.getByText('OpenAI')).toHaveCount(0)
 await expect(dialog.getByRole('radio')).toHaveCount(0)
 await dialog.getByLabel('Gemini API Key').fill('fixture-browser-key')
 await expect(dialog.getByLabel('Gemini API Key')).toHaveAttribute('type','password')
 await dialog.getByRole('button',{name:'Test & Apply'}).click()
 await expect(dialog.getByRole('status').getByText('Gemini connected.',{exact:true})).toBeVisible()
 await expect(page.getByText('Agent: Gemini · Connected',{exact:true})).toBeVisible()
 await expect(dialog.getByRole('progressbar')).toHaveAttribute('value','5')
 expect(posts).toBe(1)
 await page.screenshot({path:'../.cache/settings-agent.png',fullPage:true})
 await dialog.getByRole('button',{name:'Replace Key'}).click()
 await expect(dialog.getByLabel('Gemini API Key')).toHaveValue('')
 await dialog.getByRole('button',{name:'Disconnect'}).click()
 await expect(page.getByText('Agent: Disconnected',{exact:true})).toBeVisible()
 await page.keyboard.press('Escape');await expect(dialog).not.toBeVisible()
 await expect(page.getByRole('button',{name:'Settings',exact:true})).toBeFocused()
 expect(await page.evaluate(()=>JSON.stringify({...localStorage}))).not.toContain('fixture-browser-key')
 await expect(page.getByRole('button',{name:'Analytics',exact:true})).toBeDisabled()
})

test('System follows device changes, Light/Dark persist and gallery art stays unchanged',async({page})=>{
 await page.emulateMedia({colorScheme:'dark'})
 await page.goto('/')
 await expect(page.locator('html')).toHaveAttribute('data-theme','dark')
 const art=page.locator('.card-art img').first()
 await expect(art).toBeVisible()
 const source=await art.getAttribute('src')
 const darkBody=await page.locator('body').evaluate(element=>getComputedStyle(element).backgroundColor)
 expect(darkBody).toBe('rgb(11, 13, 19)')
 await page.getByRole('button',{name:'Settings',exact:true}).click()
 await page.getByRole('button',{name:'Appearance',exact:true}).click()
 const dialog=page.getByRole('dialog',{name:'Appearance'})
 await expect(dialog.getByLabel('System')).toBeChecked()
 await page.emulateMedia({colorScheme:'light'})
 await expect(page.locator('html')).toHaveAttribute('data-theme','light')
 const lightBody=await page.locator('body').evaluate(element=>getComputedStyle(element).backgroundColor)
 expect(lightBody).toBe('rgb(245, 246, 250)')
 await expect(dialog).toHaveCSS('background-color','rgb(255, 255, 255)')
 await page.screenshot({path:'../.cache/settings-light.png',fullPage:true})
 await dialog.getByLabel('Dark').check()
 await expect(dialog).toHaveCSS('background-color','rgb(16, 19, 27)')
 await expect(page.locator('body')).toHaveCSS('color','rgb(221, 225, 237)')
 await page.screenshot({path:'../.cache/settings-dark.png',fullPage:true})
 await dialog.getByRole('button',{name:'Done'}).click()
 await expect(art).toHaveAttribute('src',source!)
 await expect(art).toHaveCSS('filter','none')
 await page.reload();await expect(page.locator('html')).toHaveAttribute('data-theme','dark')
 expect(await page.evaluate(()=>localStorage.getItem('pokelab.appearance'))).toBe('dark')
 await page.getByRole('button',{name:'Deck Builder',exact:true}).click();await expect(page).toHaveURL(/deck-builder/)
 await expect(page.locator('html')).toHaveAttribute('data-theme','dark')
 await expect(page.getByRole('button',{name:'Settings',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Collection',exact:true}).click();await expect(page).toHaveURL(/collection/)
 await expect(page.locator('html')).toHaveAttribute('data-theme','dark')
})
