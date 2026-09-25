import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

// JSDOM has no layout observer; geometry is verified in the real browser suite.
beforeEach(()=>{
 vi.stubGlobal('ResizeObserver',class {observe(){} unobserve(){} disconnect(){}})
 vi.stubGlobal('matchMedia',vi.fn().mockReturnValue({matches:false}))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
afterEach(() => { window.history.replaceState({}, '', '/') })
