import { useEffect, useState } from 'react'
import axios from 'axios'
import Connections from './Connections'

export default function Settings({ connections, onConnect, showToast }) {
  const [competitors, setCompetitors] = useState('')
  const [savedList, setSavedList] = useState([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    axios.get('/api/settings/competitors')
      .then(r => { setCompetitors(r.data.competitors || ''); setSavedList(r.data.list || []) })
      .catch(() => {})
  }, [])

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

      {/* Competitors */}
      <div className="settings-card">
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
