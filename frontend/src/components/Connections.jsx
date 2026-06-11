import { useEffect, useState } from 'react'
import axios from 'axios'

const PLATFORMS = [
  {
    key: 'linkedin',
    label: 'LinkedIn',
    shortLabel: 'in',
    color: '#0A66C2',
    bgColor: '#EBF3FC',
    authUrl: '/api/auth/linkedin',
    idLabel: 'Client ID',
    secretLabel: 'Client Secret',
    helpUrl: 'https://www.linkedin.com/developers/apps',
    hint: 'Create an app at LinkedIn Developer Portal → Products → Sign In with LinkedIn using OpenID Connect',
  },
  {
    key: 'instagram',
    label: 'Instagram',
    shortLabel: 'IG',
    gradient: 'linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888)',
    color: '#E1306C',
    bgColor: '#FFF0F6',
    authUrl: '/api/auth/instagram',
    idLabel: 'App ID',
    secretLabel: 'App Secret',
    helpUrl: 'https://developers.facebook.com/apps',
    hint: 'Create a Meta/Facebook app → Add Instagram Basic Display product',
  },
]

function CredentialsModal({ platform, onClose, onSaved }) {
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErr('')
    if (!clientId.trim() || !clientSecret.trim()) {
      setErr('Both fields are required')
      return
    }
    setSaving(true)
    try {
      await axios.post('/api/settings/credentials', {
        platform: platform.key,
        client_id: clientId.trim(),
        client_secret: clientSecret.trim(),
      })
      onSaved()
    } catch (ex) {
      setErr(ex.response?.data?.detail || 'Failed to save credentials')
      setSaving(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.72)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div style={{
        background: '#141414',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: 12,
        padding: '28px 28px 24px',
        width: 420, maxWidth: '94vw',
        fontFamily: 'var(--font-body)',
      }} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 8,
            background: platform.gradient || platform.color,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, fontWeight: 800, color: '#fff', flexShrink: 0,
          }}>
            {platform.shortLabel}
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#fff' }}>
              Setup {platform.label}
            </div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 1 }}>
              Enter your OAuth app credentials
            </div>
          </div>
          <button onClick={onClose} style={{
            marginLeft: 'auto', background: 'none', border: 'none',
            color: 'rgba(255,255,255,0.4)', fontSize: 18, cursor: 'pointer', lineHeight: 1,
          }}>✕</button>
        </div>

        {/* Hint */}
        <div style={{
          background: 'rgba(255,255,255,0.05)', borderRadius: 8,
          padding: '10px 12px', marginBottom: 18, fontSize: 12,
          color: 'rgba(255,255,255,0.5)', lineHeight: 1.5,
        }}>
          {platform.hint}{' '}
          <a href={platform.helpUrl} target="_blank" rel="noreferrer"
            style={{ color: platform.color, textDecoration: 'none' }}>
            Developer Portal →
          </a>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: 'block', fontSize: 11, color: 'rgba(255,255,255,0.5)', marginBottom: 5, letterSpacing: '0.06em' }}>
              {platform.idLabel.toUpperCase()}
            </label>
            <input
              type="text"
              value={clientId}
              onChange={e => setClientId(e.target.value)}
              placeholder={`Paste your ${platform.idLabel}`}
              style={{
                width: '100%', boxSizing: 'border-box',
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: 7, padding: '9px 11px',
                color: '#fff', fontSize: 13,
                fontFamily: 'var(--font-mono)',
                outline: 'none',
              }}
            />
          </div>
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', fontSize: 11, color: 'rgba(255,255,255,0.5)', marginBottom: 5, letterSpacing: '0.06em' }}>
              {platform.secretLabel.toUpperCase()}
            </label>
            <input
              type="password"
              value={clientSecret}
              onChange={e => setClientSecret(e.target.value)}
              placeholder={`Paste your ${platform.secretLabel}`}
              style={{
                width: '100%', boxSizing: 'border-box',
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: 7, padding: '9px 11px',
                color: '#fff', fontSize: 13,
                fontFamily: 'var(--font-mono)',
                outline: 'none',
              }}
            />
          </div>

          {err && (
            <div style={{ fontSize: 12, color: '#FF5C5C', marginBottom: 12 }}>{err}</div>
          )}

          <div style={{ display: 'flex', gap: 10 }}>
            <button type="button" onClick={onClose} style={{
              flex: 1, padding: '9px 0',
              background: 'rgba(255,255,255,0.07)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 7, color: 'rgba(255,255,255,0.6)',
              cursor: 'pointer', fontSize: 13, fontFamily: 'var(--font-body)',
            }}>Cancel</button>
            <button type="submit" disabled={saving} style={{
              flex: 2, padding: '9px 0',
              background: platform.color,
              border: 'none', borderRadius: 7,
              color: '#fff', cursor: 'pointer',
              fontSize: 13, fontWeight: 600,
              fontFamily: 'var(--font-body)',
              opacity: saving ? 0.7 : 1,
            }}>
              {saving ? 'Saving…' : `Save & Connect →`}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Connections({ connections, onConnect, compact = false }) {
  const [credStatus, setCredStatus] = useState({ linkedin: false, instagram: false })
  const [modalPlatform, setModalPlatform] = useState(null)

  useEffect(() => {
    axios.get('/api/settings/status')
      .then(r => setCredStatus(r.data))
      .catch(() => {})
  }, [])

  const handleConnect = (platform) => {
    if (credStatus[platform.key]) {
      // Credentials already stored — go straight to OAuth
      window.location.href = platform.authUrl
    } else {
      // Need to enter credentials first
      setModalPlatform(platform)
    }
  }

  const handleModalSaved = () => {
    // Credentials saved — now refresh status and redirect to OAuth
    const platform = modalPlatform
    setModalPlatform(null)
    setCredStatus(s => ({ ...s, [platform.key]: true }))
    // Small delay so DB write commits before redirect
    setTimeout(() => { window.location.href = platform.authUrl }, 200)
  }

  const handleDisconnect = async (platformKey) => {
    try {
      await axios.delete(`/api/connections/${platformKey}`)
      onConnect()
    } catch (e) {
      console.error(e)
    }
  }

  const handleClearCreds = async (platformKey) => {
    try {
      await axios.delete(`/api/settings/credentials/${platformKey}`)
      setCredStatus(s => ({ ...s, [platformKey]: false }))
    } catch (e) { console.error(e) }
  }

  if (compact) {
    return (
      <>
        {modalPlatform && (
          <CredentialsModal
            platform={modalPlatform}
            onClose={() => setModalPlatform(null)}
            onSaved={handleModalSaved}
          />
        )}
        <div style={{ display: 'flex', gap: 6 }}>
          {PLATFORMS.map(p => {
            const connected = connections[p.key]
            return (
              <button
                key={p.key}
                onClick={() => connected ? handleDisconnect(p.key) : handleConnect(p)}
                style={{
                  fontSize: 12, fontWeight: 600,
                  padding: '4px 10px', borderRadius: 6, border: '1px solid',
                  borderColor: connected ? p.color : 'rgba(255,255,255,0.2)',
                  background: connected ? p.bgColor : 'transparent',
                  color: connected ? p.color : 'rgba(255,255,255,0.7)',
                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
                  fontFamily: 'var(--font-body)', transition: 'all 0.15s',
                }}
                title={connected ? `${p.label}: ${connected.username} — click to disconnect` : `Connect ${p.label}`}
              >
                <span style={{
                  width: 14, height: 14, borderRadius: 3,
                  background: p.gradient || p.color,
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 8, color: 'white', fontWeight: 800,
                }}>
                  {p.shortLabel[0]}
                </span>
                {connected ? `✓ ${p.label}` : p.label}
              </button>
            )
          })}
        </div>
      </>
    )
  }

  return (
    <div>
      {modalPlatform && (
        <CredentialsModal
          platform={modalPlatform}
          onClose={() => setModalPlatform(null)}
          onSaved={handleModalSaved}
        />
      )}

      <div style={{ marginBottom: 16 }}>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Connect your accounts to post directly. Enter your OAuth app credentials once —
          they're stored locally and never leave your device.
        </p>
      </div>

      {PLATFORMS.map(p => {
        const connected = connections[p.key]
        const hasCredentials = credStatus[p.key]
        return (
          <div
            key={p.key}
            className={`connection-card ${connected ? `connected-${p.key === 'linkedin' ? 'li' : 'ig'}` : ''}`}
          >
            <div style={{
              width: 36, height: 36, borderRadius: 8,
              background: p.gradient || p.color,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 800, color: 'white', flexShrink: 0,
            }}>
              {p.shortLabel}
            </div>

            <div className="conn-info" style={{ flex: 1 }}>
              <div className="conn-platform">{p.label}</div>
              <div className={`conn-status ${connected ? 'connected' : ''}`}>
                {connected
                  ? `✓ Connected as ${connected.username || 'account'}`
                  : hasCredentials
                    ? 'Credentials saved — ready to connect'
                    : 'No credentials configured'
                }
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {connected ? (
                <button className="btn btn-danger" onClick={() => handleDisconnect(p.key)}>
                  Disconnect
                </button>
              ) : (
                <>
                  {hasCredentials && (
                    <button
                      className="btn btn-sm"
                      onClick={() => handleClearCreds(p.key)}
                      style={{ fontSize: 11, opacity: 0.5, borderColor: 'rgba(255,255,255,0.2)', color: 'rgba(255,255,255,0.5)' }}
                      title="Clear saved credentials"
                    >
                      ✕ reset
                    </button>
                  )}
                  <button
                    className="btn btn-sm"
                    onClick={() => handleConnect(p)}
                    style={{ borderColor: p.color, color: p.color }}
                  >
                    {hasCredentials ? 'Connect →' : 'Setup →'}
                  </button>
                </>
              )}
            </div>
          </div>
        )
      })}

      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 12, lineHeight: 1.6 }}>
        🔒 OAuth 2.0 — your password never touches this app. Credentials are stored in a local SQLite database only.
      </p>
    </div>
  )
}
