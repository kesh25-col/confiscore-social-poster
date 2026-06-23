import { useState } from 'react'
import axios from 'axios'

export default function Login({ onSuccess }) {
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setErr('')
    if (!password.trim()) { setErr('Enter the access password'); return }
    setLoading(true)
    try {
      const { data } = await axios.post('/api/login', { password })
      const token = data.token || ''
      localStorage.setItem('cs_auth', token)
      axios.defaults.headers.common['X-Auth-Token'] = token
      onSuccess()
    } catch (ex) {
      setErr(ex.response?.status === 401 ? 'Incorrect password' : 'Login failed — try again')
      setLoading(false)
    }
  }

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <div className="login-logo">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="8" stroke="white" strokeWidth="2" />
            <path d="M9 12.5l2 2 4-4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <h1 className="login-title">Confiscore Social Poster</h1>
        <p className="login-sub">Enter the team access password to continue.</p>
        <input
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          placeholder="Access password"
          autoFocus
        />
        {err && <div className="login-err">{err}</div>}
        <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 12 }}>
          {loading ? <span className="spin" /> : 'Enter →'}
        </button>
      </form>
    </div>
  )
}
