import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, test, vi } from 'vitest'
import { FinishImage } from './FinishImage'
import { CardImage, CardTile } from './CardTile'
import type { Card } from './api'

const card:Card={id:'test-1',name:'Test',category:'Pokemon',localId:1,set:{id:'test'},legal:{},image_url:'/card.webp',legality_provenance:{source:'TCGdex',checked_at:'today'},ownership:{functional_id:'f',library_id:'f',variant:'holo',quantity:1,functional_total:1,library_total:1}}
test.each(['normal','unspecified','unknown',undefined])('%s leaves the original image without a foil layer',finish=>{
 const {container}=render(<FinishImage finish={finish} src="/card.webp" alt="Original"/>)
 expect(container.querySelector('.finish-light')).toBeNull()
 expect(screen.getByRole('img')).toHaveAttribute('src','/card.webp')
})
test.each(['holo','reverse'])('%s has a decorative layer without changing image event targets',finish=>{
 const enter=vi.fn(),leave=vi.fn(),click=vi.fn()
 const {container}=render(<FinishImage finish={finish} src="/card.webp" alt="Original" onPointerEnter={e=>enter(e.currentTarget.tagName)} onPointerLeave={leave} onClick={click}/>)
 expect(container.querySelector('.finish-surface')).toHaveAttribute('data-finish',finish)
 expect(container.querySelector('.finish-light')).toHaveAttribute('aria-hidden','true')
 fireEvent.pointerEnter(container.querySelector('.finish-surface')!);expect(enter).not.toHaveBeenCalled()
 fireEvent.pointerEnter(screen.getByRole('img'));expect(enter).toHaveBeenCalledWith('IMG')
 fireEvent.click(screen.getByRole('img'));expect(click).toHaveBeenCalledOnce()
 fireEvent.pointerLeave(screen.getByRole('img'));expect(leave).toHaveBeenCalledOnce()
})
test('reduced motion does not activate pointer-driven lighting',()=>{
 vi.stubGlobal('matchMedia',vi.fn().mockReturnValue({matches:true}))
 const {container}=render(<FinishImage finish="reverse" alt="Reverse"/>)
 fireEvent.pointerMove(screen.getByRole('img'),{clientX:40,clientY:20})
 expect(container.querySelector('.finish-surface')).not.toHaveAttribute('data-lit')
 expect(container.querySelector('.finish-light')).not.toBeNull()
})
test('autonomous phases are reproducible and distinguish exact finishes',()=>{
 const {container,rerender}=render(<FinishImage finish="holo" src="/card/low.webp" alt="Card"/>)
 const delay=()=>container.querySelector<HTMLElement>('.finish-shimmer')!.style.animationDelay
 const original=delay()
 rerender(<FinishImage finish="holo" src="/card/high.webp" alt="Card"/>);expect(delay()).toBe(original)
 rerender(<FinishImage finish="reverse" src="/card/high.webp" alt="Card"/>);expect(delay()).not.toBe(original)
})
test('exact Collection gets its known finish; functional gallery remains neutral',()=>{
 const {container,rerender}=render(<MemoryRouter><CardTile card={card} exact/></MemoryRouter>)
 expect(container.querySelector('[data-finish="holo"]')).not.toBeNull()
 rerender(<MemoryRouter><CardTile card={card}/></MemoryRouter>)
 expect(container.querySelector('.finish-light')).toBeNull()
})
test('finish changes and failed images remove the old treatment',()=>{
 const {container,rerender}=render(<CardImage card={card}/>)
 rerender(<CardImage card={{...card,ownership:{...card.ownership!,variant:'normal'}}}/>)
 expect(container.querySelector('.finish-light')).toBeNull()
 rerender(<CardImage card={card}/>);fireEvent.error(screen.getByRole('img'))
 expect(container.querySelector('.finish-light')).toBeNull()
 expect(screen.getByText('Image unavailable')).toBeInTheDocument()
})
test('foil image preserves the exact 500ms competitive delay and image-only boundary',async()=>{
 vi.useFakeTimers();vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false}))
 try{
  const {container}=render(<MemoryRouter><CardTile card={card} exact competitive/></MemoryRouter>)
  fireEvent.pointerEnter(container.querySelector('.finish-surface')!)
  await act(async()=>vi.advanceTimersByTime(600));expect(screen.queryByRole('dialog')).toBeNull()
  fireEvent.pointerEnter(screen.getByRole('img'))
  await act(async()=>vi.advanceTimersByTime(499));expect(screen.queryByRole('dialog')).toBeNull()
  await act(async()=>vi.advanceTimersByTime(1));expect(screen.getByRole('dialog')).toBeInTheDocument()
 }finally{vi.useRealTimers()}
})
