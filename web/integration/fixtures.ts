// Existing browser suite, with deterministic local artwork and no CDN requests.
import {test as base,type BrowserContext} from '@playwright/test'
export * from '@playwright/test'

export async function offlineArtwork(context:BrowserContext) {
 await context.route('**/*',async route=>{
  const request=route.request(),url=new URL(request.url())
  if(['127.0.0.1','localhost'].includes(url.hostname))return route.continue()
  if(request.resourceType()==='image')return route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="350" height="490"><rect width="350" height="490" fill="#29405c"/><text x="20" y="50" fill="white">Offline artwork fixture</text></svg>'})
  return route.abort()
 })
}

export const test=base.extend({
 context:async({context},use)=>{await offlineArtwork(context);await use(context)}
})
