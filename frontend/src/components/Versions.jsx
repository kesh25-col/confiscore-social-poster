const VOICE_COLORS = {
  debasis: { bg: '#F0F4FF', border: '#3B5BDB', text: '#1A3090' },
  brand:   { bg: '#F0FDF4', border: '#16A34A', text: '#15803D' },
  data:    { bg: '#FFFBEB', border: '#D97706', text: '#92400E' },
  inspiring: { bg: '#FDF4FF', border: '#9333EA', text: '#6B21A8' }
}

export default function Versions({ versions, selectedVersion, setSelectedVersion, platforms }) {
  if (!versions) return null

  const keys = Object.keys(versions)
  const displayPlatform = platforms.includes('li') ? 'li' : 'ig'

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          Click a version to select it — then preview below and post
        </p>
        <span style={{ fontSize: 12, color: 'var(--accent)', fontWeight: 600 }}>
          {versions[selectedVersion]?.name} selected
        </span>
      </div>
      <div className="versions-grid">
        {keys.map(key => {
          const v = versions[key]
          const colors = VOICE_COLORS[key] || VOICE_COLORS.brand
          const text = v?.content?.[displayPlatform] || v?.content?.[platforms[0]] || ''

          return (
            <div
              key={key}
              className={`version-card ${selectedVersion === key ? 'selected' : ''}`}
              onClick={() => setSelectedVersion(key)}
            >
              <div className="version-header" style={{ background: selectedVersion === key ? colors.bg : undefined }}>
                <div>
                  <div className="version-name" style={{ color: selectedVersion === key ? colors.text : undefined }}>
                    {v.name}
                  </div>
                  <div className="version-desc">{v.description}</div>
                </div>
                {selectedVersion === key && (
                  <span className="version-selected-badge" style={{ background: colors.border }}>
                    Selected
                  </span>
                )}
              </div>
              <div className="version-body">
                <div className={`version-platform-label ${displayPlatform}`}>
                  {displayPlatform === 'li' ? 'LinkedIn' : 'Instagram'}
                </div>
                <div className="version-text">{text || 'No content'}</div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
