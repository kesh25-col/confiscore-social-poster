import axios from 'axios'

const PLATFORM_NAMES = { li: 'LinkedIn', ig: 'Instagram' }
const VOICE_NAMES = {
  debasis: 'Himaan Chatterji Voice',
  brand: 'Brand Voice',
  data: 'Data-Driven',
  inspiring: 'Inspiring'
}

export default function Drafts({ drafts, connections, onRefresh, showToast }) {
  const handleDelete = async (id) => {
    try {
      await axios.delete(`/api/drafts/${id}`)
      showToast('Draft deleted', 'info')
      onRefresh()
    } catch { showToast('Delete failed', 'error') }
  }

  if (!drafts.length) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📭</div>
        <p>No drafts yet — generate and save your first post.</p>
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ fontSize: 18 }}>Drafts & Posts</h2>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{drafts.length} total</span>
      </div>

      {drafts.map(draft => {
        const previewVersion = draft.selected_version || Object.keys(draft.versions || {})[0]
        const previewPlatform = draft.platforms?.[0]
        const previewText = draft.versions?.[previewVersion]?.content?.[previewPlatform] || ''
        const date = new Date(draft.created_at + 'Z').toLocaleString('en-IN', {
          day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
        })

        return (
          <div key={draft.id} className="draft-item">
            <div className="draft-top">
              <div className="draft-desc">{draft.description}</div>
              <div className="draft-meta">
                <span className="draft-date">{date}</span>
                <span className={`status-badge status-${draft.status}`}>
                  {draft.status}
                </span>
              </div>
            </div>
            <div className="draft-platforms">
              {draft.platforms?.map(p => (
                <span key={p} className={`plat-pill ${p}`}>{PLATFORM_NAMES[p]}</span>
              ))}
              {previewVersion && (
                <span style={{ fontSize: 10.5, color: 'var(--text-muted)', padding: '2px 0' }}>
                  · {VOICE_NAMES[previewVersion] || previewVersion}
                </span>
              )}
            </div>
            {previewText && (
              <div className="draft-preview-text">{previewText}</div>
            )}
            <div className="draft-actions">
              <button
                className="btn btn-danger"
                onClick={() => handleDelete(draft.id)}
              >
                ✕ Delete
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
