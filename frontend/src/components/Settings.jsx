import { useEffect, useState } from 'react'
import axios from 'axios'
import Connections from './Connections'
import { fmtTokens } from '../utils'

export default function Settings({ connections, onConnect, showToast, usage, onRefreshUsage }) {
  const [competitors, setCompetitors] = useState('')
  const [savedList, setSavedList] = useState([])
  const [saving, setSaving] = useState(false)
  const [resetting, setResetting] = useState(false)

  useEffect(() => {
    axios.get('/api/settings/competitors')
      .then(r => { setCompetitors(r.data.competitors || ''); setSavedList(r.data.list || []) })
      .catch(() => {})
    onRefreshUsage?.()
  }, [])

  const resetUsage = async () => {
    if (!window.confirm('Reset the all-time token counter to zero? This cannot be undone.')) return
    setResetting(true)
    try {
      await axios.post('/api/usage/reset')
      onRefreshUsage?.()
      showToast('Token counter reset', 'success')
    } catch {
      showToast('Failed to reset', 'error')
    } finally {
      setResetting(false)
    }
  }

  const saveCompetitors = async () => {
    setSaving(true)
    try {
      const { data } = await axios.post('/api/settings/competitors', { competitors })
      setSavedList(data.list || [])
      showToast('Competitors saved', 'success')
    } catch {
      showToast('Failed to save', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ maxWidth: 720 }}>
      <h2 style={{ fontSize: 18, marginBottom: 4 }}>Settings</h2>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>
        Configure connections and the competitors used for auto-research.
      </p>

      {/* API Token Usage */}
      <div className="settings-card">
        <div className="settings-card-title">⚡ API Token Usage</div>
        <p style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: 14 }}>
          Claude API tokens used across all generations. Anthropic bills pay-as-you-go, so this is
          your actual consumption and an estimated cost (Sonnet rates: ${usage?.price_in ?? 3}/M in, ${usage?.price_out ?? 15}/M out).
        </p>

        {/* All-time (never resets) */}
        <div className="usage-section-lbl">All-time (never resets)</div>
        <div className="usage-grid">
          <div className="usage-stat">
            <div className="usage-stat-num">{fmtTokens(usage?.lifetime?.total_tokens)}</div>
            <div className="usage-stat-lbl">Total tokens</div>
          </div>
          <div className="usage-stat">
            <div className="usage-stat-num">{fmtTokens(usage?.lifetime?.input_tokens)}</div>
            <div className="usage-stat-lbl">Input</div>
          </div>
          <div className="usage-stat">
            <div className="usage-stat-num">{fmtTokens(usage?.lifetime?.output_tokens)}</div>
            <div className="usage-stat-lbl">Output</div>
          </div>
          <div className="usage-stat">
            <div className="usage-stat-num" style={{ color: 'var(--accent)' }}>~${(usage?.lifetime?.est_cost_usd ?? 0).toFixed(2)}</div>
            <div className="usage-stat-lbl">Est. cost</div>
          </div>
          <div className="usage-stat">
            <div className="usage-stat-num">{usage?.lifetime?.calls ?? 0}</div>
            <div className="usage-stat-lbl">API calls</div>
          </div>
        </div>

        {/* Current period (resettable) */}
        <div className="usage-section-lbl" style={{ marginTop: 16 }}>Current period (resettable)</div>
        <div className="usage-grid">
          <div className="usage-stat">
            <div className="usage-stat-num">{fmtTokens(usage?.total_tokens)}</div>
            <div className="usage-stat-lbl">Total tokens</div>
          </div>
          <div className="usage-stat">
            <div className="usage-stat-num" style={{ color: 'var(--accent)' }}>~${(usage?.est_cost_usd ?? 0).toFixed(2)}</div>
            <div className="usage-stat-lbl">Est. cost</div>
          </div>
          <div className="usage-stat">
            <div className="usage-stat-num">{usage?.calls ?? 0}</div>
            <div className="usage-stat-lbl">API calls</div>
          </div>
        </div>
        <button
          className="btn btn-secondary"
          style={{ width: 'auto', padding: '8px 18px', marginTop: 14 }}
          onClick={resetUsage}
          disabled={resetting}
        >
          {resetting ? <span className="spin" /> : '↺'} Reset current period
        </button>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
          Resets the period counter only — your all-time total is always preserved.
        </p>
      </div>

      {/* Competitors */}
      <div className="settings-card" style={{ marginTop: 18 }}>
        <div className="settings-card-title">🏁 Competitors</div>
        <p style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: 12 }}>
          List your competitors — one per line (name or website). Auto-research searches these to find
          angles they're not covering, so your posts stand apart.
        </p>
        <textarea
          rows={5}
          value={competitors}
          onChange={e => setCompetitors(e.target.value)}
          placeholder={'HireVue\nPymetrics\nhttps://www.criteriacorp.com\nTraitify'}
          style={{ marginBottom: 10 }}
        />
        {savedList.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
            {savedList.map((c, i) => (
              <span key={i} className="plat-pill" style={{ background: 'var(--bg4)', color: 'var(--white-dim)', textTransform: 'none' }}>
                {c}
              </span>
            ))}
          </div>
        )}
        <button className="btn btn-primary" style={{ width: 'auto', padding: '10px 22px' }} onClick={saveCompetitors} disabled={saving}>
          {saving ? <span className="spin" /> : '↓'} Save competitors
        </button>
      </div>

      {/* Connections */}
      <div className="settings-card" style={{ marginTop: 18 }}>
        <div className="settings-card-title">🔗 Platform Connections</div>
        <Connections connections={connections} onConnect={onConnect} />
      </div>
    </div>
  )
}
