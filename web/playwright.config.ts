import { defineConfig } from '@playwright/test'
import path from 'node:path'
const root = path.resolve('..')
const python = process.env.POKELAB_TEST_PYTHON || path.join(root,'.venv',process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
export default defineConfig({
 testDir:'./integration',timeout:60000,workers:1,
 use:{baseURL:'http://127.0.0.1:5174',viewport:{width:1440,height:1000}},
 webServer:[
  {command:`"${python}" tests/serve_web_acceptance.py`,cwd:root,url:'http://127.0.0.1:8002/api/v1/status',reuseExistingServer:false,timeout:30000},
  {command:'npm run dev -- --port 5174',env:{POKELAB_API_TARGET:'http://127.0.0.1:8002'},url:'http://127.0.0.1:5174',reuseExistingServer:false,timeout:30000}
 ]
})
