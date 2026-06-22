import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import axios from 'axios'
import './index.css'
import App from './App.jsx'

// Attach the saved auth token (if any) before the app makes any request.
// Locally there's no gate and no token, so this is a no-op.
const savedToken = localStorage.getItem('cs_auth')
if (savedToken) axios.defaults.headers.common['X-Auth-Token'] = savedToken

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
