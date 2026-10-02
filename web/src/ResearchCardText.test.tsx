import {render,screen,fireEvent,waitFor} from '@testing-library/react'
import {test,expect,vi} from 'vitest'
import {ResearchCardText} from './ResearchCardText'

test('cited card name reuses readable preview, lazy exact printing lookup and evidence click',async()=>{
 const inspect=vi.fn(),fetch=vi.fn(async(_url:string,_options?:RequestInit)=>({ok:true,json:async()=>({card:{id:'coal-1',image_url:'/art/low.webp'}})}))
 vi.stubGlobal('fetch',fetch)
 render(<ResearchCardText text="Coalossal removes two cards." cards={[{name:'Coalossal',printing:'coal-1',id:'ev-coal'}]} inspect={inspect}/>)
 expect(fetch).not.toHaveBeenCalled()
 const name=screen.getByRole('button',{name:'Coalossal'})
 fireEvent.pointerEnter(name)
 await waitFor(()=>expect(screen.getByRole('img',{name:'Coalossal card artwork'})).toHaveAttribute('src','/art/high.webp'))
 expect(screen.getByRole('tooltip')).toBeVisible()
 expect(fetch).toHaveBeenCalledTimes(1)
 expect(fetch.mock.calls[0][0]).toBe('/api/v1/cards/coal-1?include_image=true')
 fireEvent.click(name);expect(inspect).toHaveBeenCalledWith('ev-coal')
 fireEvent.keyDown(window,{key:'Escape'});expect(screen.queryByRole('tooltip')).toBeNull()
 fireEvent.focus(name);expect(screen.getByRole('tooltip')).toBeVisible()
 fireEvent.error(screen.getByRole('img'));expect(screen.getByText('Image unavailable')).toBeVisible()
 expect(fetch).toHaveBeenCalledTimes(1)
})

test('uncited names stay plain and matching preserves complete names',()=>{
 render(<ResearchCardText text="Mega Coalossal and Coalossal." cards={[{name:'Mega Coalossal',printing:'mega-1',id:'ev-mega'}]} inspect={()=>{}}/>)
 expect(screen.getAllByRole('button')).toHaveLength(1)
 expect(screen.getByRole('button')).toHaveTextContent('Mega Coalossal')
})
