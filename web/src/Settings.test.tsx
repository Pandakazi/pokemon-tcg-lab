import {act,fireEvent,render,screen,waitFor} from '@testing-library/react'
import {beforeEach,afterEach,expect,test,vi} from 'vitest'
import {SettingsControl} from './Settings'
import {ConversationPanel} from './ConversationPanel'
import {publishAgentStatus} from './AgentStatus'
import {APPEARANCE_KEY} from './Appearance'

vi.mock('./DeckBuilder',()=>({useDeck:()=>null}))
vi.mock('./Competitive',()=>({useCompetitiveTimeframe:()=>({window:'30'})}))
const disconnected={provider:null,connected:false,has_key:false,managed:false,storage:'external'}
const connected={provider:'gemini',connected:true,has_key:true,managed:true,storage:'encrypted'}
const ok=(value:unknown)=>({ok:true,json:async()=>value})
const events=[{stage:'validating',message:'Validating API key…'},{stage:'connecting',message:'Connecting to Gemini…'},
 {stage:'testing',message:'Checking Agent response…'},{stage:'saving',message:'Saving securely…'},
 {stage:'connected',message:'Gemini connected.',settings:connected}]
function stream(value=events) {
 return {ok:true,body:new ReadableStream({start(controller){
  const text=value.map(event=>JSON.stringify(event)+'\n').join(''),bytes=new TextEncoder().encode(text)
  controller.enqueue(bytes.slice(0,23));controller.enqueue(bytes.slice(23));controller.close()
 }})}
}
beforeEach(()=>{
 localStorage.clear();document.documentElement.removeAttribute('data-theme')
 HTMLDialogElement.prototype.showModal=function(){this.open=true}
 HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new Event('close'))}
})
afterEach(()=>{localStorage.clear()})
async function openAgent() {
 fireEvent.click(screen.getByRole('button',{name:'Settings'}))
 fireEvent.click(screen.getByRole('button',{name:'Agent Settings'}))
 await waitFor(()=>expect(screen.queryByText('Loading Agent settings…')).not.toBeInTheDocument())
}

test('Settings menu has bounded choices and exactly one provider with a masked key',async()=>{
 const fetch=vi.fn().mockResolvedValue(ok(disconnected));vi.stubGlobal('fetch',fetch)
 render(<SettingsControl/>);await openAgent()
 expect(screen.getByText('AI provider: Gemini')).toBeInTheDocument()
 expect(screen.queryByText('OpenAI')).not.toBeInTheDocument()
 expect(screen.queryByRole('radio')).not.toBeInTheDocument()
 expect(screen.getByLabelText('Gemini API Key')).toHaveAttribute('type','password')
 expect(screen.getByRole('button',{name:'Test & Apply'})).toBeDisabled()
 fireEvent.click(screen.getByRole('button',{name:'Done'}))
 expect(screen.getByRole('button',{name:'Settings'})).toHaveFocus()
 expect(fetch).toHaveBeenCalledTimes(1)
})

test('live streamed progress holds the modal and prevents duplicate submissions; key never persists in browser',async()=>{
 let controller!:ReadableStreamDefaultController
 const fetch=vi.fn(async(url:string)=>url.endsWith('test-apply')?{ok:true,body:new ReadableStream({start(value){controller=value}})}:ok(disconnected))
 vi.stubGlobal('fetch',fetch);render(<SettingsControl/>);await openAgent()
 fireEvent.change(screen.getByLabelText('Gemini API Key'),{target:{value:'fixture-api-key'}})
 fireEvent.click(screen.getByRole('button',{name:'Test & Apply'}));fireEvent.click(screen.getByRole('button',{name:'Test & Apply'}))
 expect(screen.getByLabelText('Gemini API Key')).toHaveValue('');expect(screen.getByRole('button',{name:'Done'})).toBeDisabled()
 await act(async()=>{controller.enqueue(new TextEncoder().encode(JSON.stringify(events[0])+'\n'+JSON.stringify(events[1])+'\n'))})
 expect(screen.getByRole('status')).toHaveTextContent('Connecting to Gemini…')
 expect(screen.getByLabelText('Connection progress')).toHaveAttribute('value','2')
 await act(async()=>{controller.enqueue(new TextEncoder().encode(events.slice(2).map(value=>JSON.stringify(value)+'\n').join('')));controller.close()})
 expect(await screen.findByRole('button',{name:'Replace Key'})).toBeEnabled()
 expect(screen.getByText('Agent: Gemini · Connected')).toBeInTheDocument()
 expect(screen.getByRole('dialog')).toBeInTheDocument()
 expect(fetch.mock.calls.filter(([url])=>url.endsWith('test-apply'))).toHaveLength(1)
 expect(Object.values(localStorage).join('')).not.toContain('fixture-api-key')
})

test('failed replacement keeps current status and supports explicit retry; disconnect refreshes the Agent',async()=>{
 const changed=vi.fn();window.addEventListener('pokelab-agent-settings-changed',changed)
 const fetch=vi.fn(async(url:string)=>url.endsWith('test-apply')?stream([{stage:'failed',message:'The API key was rejected. Check it and try again.'} as typeof events[number]]):url.endsWith('disconnect')?ok({ok:true,settings:{...disconnected,managed:true}}):ok(connected))
 vi.stubGlobal('fetch',fetch);render(<SettingsControl/>);await openAgent()
 fireEvent.click(screen.getByRole('button',{name:'Replace Key'}))
 fireEvent.change(screen.getByLabelText('Gemini API Key'),{target:{value:'invalid-fixture-key'}})
 fireEvent.click(screen.getByRole('button',{name:'Test & Apply'}))
 expect(await screen.findByRole('alert')).toHaveTextContent('API key was rejected')
 expect(screen.getByText('Agent: Gemini · Connected')).toBeInTheDocument()
 expect(changed).not.toHaveBeenCalled()
 fireEvent.click(screen.getByRole('button',{name:'Disconnect'}))
 await screen.findByText('Agent: Disconnected')
 expect(screen.getByLabelText('Gemini API Key')).toHaveValue('');expect(changed).toHaveBeenCalledTimes(1)
 window.removeEventListener('pokelab-agent-settings-changed',changed)
})

test('disconnect failure retains the connection; closing clears the pasted key',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>url.endsWith('disconnect')?{ok:false,json:async()=>({ok:false,message:'The Agent is busy.'})}:ok(connected)))
 render(<SettingsControl/>);await openAgent();fireEvent.click(screen.getByRole('button',{name:'Replace Key'}))
 fireEvent.change(screen.getByLabelText('Gemini API Key'),{target:{value:'fixture-key'}})
 fireEvent.click(screen.getByRole('button',{name:'Disconnect'}))
 expect(await screen.findByRole('alert')).toHaveTextContent('busy')
 expect(screen.getByText('Agent: Gemini · Connected')).toBeInTheDocument()
 fireEvent.click(screen.getByRole('button',{name:'Done'}));await openAgent()
 fireEvent.click(screen.getByRole('button',{name:'Replace Key'}))
 expect(screen.getByLabelText('Gemini API Key')).toHaveValue('')
})

test('legacy backend provider remains disconnectable without an OpenAI preview option',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(ok({...connected,provider:'openai'})))
 render(<SettingsControl/>);await openAgent()
 expect(screen.queryByText(/OpenAI/)).not.toBeInTheDocument()
 expect(screen.getByText('AI provider: Gemini')).toBeInTheDocument()
 expect(screen.getByLabelText('Gemini API Key')).toHaveAttribute('type','password')
 expect(screen.getByRole('button',{name:'Disconnect'})).toBeEnabled()
})

test('System is default, tracks device changes; explicit Light/Dark persist and survive remount',async()=>{
 let update!:()=>void
 const media={matches:true,addEventListener:vi.fn((_event,callback)=>{update=callback}),removeEventListener:vi.fn()}
 vi.stubGlobal('matchMedia',()=>media)
 const view=render(<SettingsControl/>);expect(document.documentElement.dataset.theme).toBe('dark')
 fireEvent.click(screen.getByRole('button',{name:'Settings'}));fireEvent.click(screen.getByRole('button',{name:'Appearance'}))
 expect(screen.getByLabelText('System')).toBeChecked()
 act(()=>{media.matches=false;update()});expect(document.documentElement.dataset.theme).toBe('light')
 fireEvent.click(screen.getByLabelText('Dark'));expect(localStorage.getItem(APPEARANCE_KEY)).toBe('dark')
 act(()=>{media.matches=false;update()});expect(document.documentElement.dataset.theme).toBe('dark')
 view.unmount();render(<SettingsControl/>);expect(document.documentElement.dataset.theme).toBe('dark')
 fireEvent.click(screen.getByRole('button',{name:'Settings'}));fireEvent.click(screen.getByRole('button',{name:'Appearance'}))
 fireEvent.click(screen.getByLabelText('Light'));expect(document.documentElement.dataset.theme).toBe('light')
 expect(localStorage.getItem(APPEARANCE_KEY)).toBe('light')
})

test('bad appearance preference falls back to System; unavailable storage is session only',()=>{
 localStorage.setItem(APPEARANCE_KEY,'invalid')
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('blocked')})
 render(<SettingsControl/>);fireEvent.click(screen.getByRole('button',{name:'Settings'}));fireEvent.click(screen.getByRole('button',{name:'Appearance'}))
 expect(screen.getByLabelText('System')).toBeChecked()
 fireEvent.click(screen.getByLabelText('Dark'));expect(screen.getByRole('alert')).toHaveTextContent('session')
 expect(document.documentElement.dataset.theme).toBe('dark');vi.restoreAllMocks()
})

test('provider update refreshes existing conversation status without clearing prior turns',async()=>{
 let statusCalls=0
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>{
  if(url.endsWith('/agent/status')){statusCalls++;return ok({version:'pokelab-research-v1',available:true,provider:statusCalls===1?'gemini':'openai',model:'fixture-model'})}
  if(url.endsWith('/agent/research'))return ok({status:'answered',conversation_id:'a'.repeat(32),answer:{paragraphs:[{text:'Saved conversational answer',evidence:[]}],facts:[],notices:[]}})
  if(url.endsWith('test-apply'))return stream()
  return ok(disconnected)
 }))
 render(<><SettingsControl/><ConversationPanel open toggle={()=>{}}/></>)
 await screen.findByText('Agent: Gemini · Connected')
 fireEvent.change(screen.getByLabelText('Ask PokéLab'),{target:{value:'Hello'}})
 fireEvent.click(screen.getByRole('button',{name:'Ask'}));await screen.findByText('Saved conversational answer')
 await openAgent();fireEvent.change(screen.getByLabelText('Gemini API Key'),{target:{value:'fixture-key'}})
 fireEvent.click(screen.getByRole('button',{name:'Test & Apply'}));await screen.findByRole('button',{name:'Replace Key'})
 await waitFor(()=>expect(statusCalls).toBe(2));expect(screen.getByText('Saved conversational answer')).toBeInTheDocument()
})

test('connection status receives existing Agent status even with the settings dialog closed',()=>{
 render(<SettingsControl/>)
 act(()=>publishAgentStatus({available:true,provider:'gemini'}))
 expect(screen.getByText('Agent: Gemini · Connected')).toBeInTheDocument()
})
