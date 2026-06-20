import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import Composer from './components/Composer'
import Versions from './components/Versions'
import Preview from './components/Preview'
import ImageUpload from './components/ImageUpload'
import Connections from './components/Connections'
import Drafts from './components/Drafts'
import Toast from './components/Toast'

const API = '/api'

export default function App() {
  const [view, setView] = useState('compose') // compose | drafts
  const [platforms, setPlatforms] = useState(['li'])
  const [description, setDescription] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generationStep, setGenerationStep] = useState(0)
  const [versions, setVersions] = useState(null)
  const [selectedVersion, setSelectedVersion] = useState(null)
  const [previewPlatform, setPreviewPlatform] = useState('li')
  const [imageUrl, setImageUrl] = useState(null)
  const [imagePath, setImagePath] = useState(null)
  const [connections, setConnections] = useState({})
  const [drafts, setDrafts] = useState([])
  const [toasts, setToasts] = useState([])
  const [saving, setSaving] = useState(false)
  const [posting, setPosting] = useState(false)
  const [savedDraftId, setSavedDraftId] = useState(null)

  // Load connections and drafts on mount
  useEffect(() => {
    loadConnections()
    loadDrafts()

    // Check if returning from OAuth
    const params = new URLSearchParams(window.location.search)
    const connected = params.get('connected')
    if (connected) {
      showToast(`${connected} connected successfully!`, 'success')
      window.history.replaceState({}, '', window.location.pathname)
      loadConnections()
    }
  }, [])

  const loadConnections = async () => {
    try {
      const { data } = await axios.get(`${API}/connections`)
      setConnections(data)
    } catch (e) { console.error(e) }
  }

  const loadDrafts = async () => {
    try {
      const { data } = await axios.get(`${API}/drafts`)
      setDrafts(data)
    } catch (e) { console.error(e) }
  }

  const showToast = useCallback((message, type = 'info') => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3000)
  }, [])

  const handleGenerate = async () => {
    if (!description.trim()) { showToast('Enter a description first', 'error'); return }
    if (!platforms.length) { showToast('Select at least one platform', 'error'); return }

    setGenerating(true)
    setVersions(null)
    setSelectedVersion(null)
    setSavedDraftId(null)
    setGenerationStep(1)

    // Simulate step progression
    const stepTimer = setInterval(() => {
      setGenerationStep(s => Math.min(s + 1, 3))
    }, 2000)

    try {
      const { data } = await axios.post(`${API}/generate`, {
        description: description.trim(),
        platforms
      })
      setVersions(data.versions)
      setSelectedVersion(Object.keys(data.versions)[0])
      setPreviewPlatform(platforms[0])
      showToast(data.search_used ? '✓ Generated with real-time web data' : '✓ Generated successfully', 'success')
    } catch (e) {
      showToast(e.response?.data?.detail || 'Generation failed', 'error')
    } finally {
      clearInterval(stepTimer)
      setGenerating(false)
      setGenerationStep(0)
    }
  }

  const handleSaveDraft = async () => {
    if (!versions) return
    setSaving(true)
    try {
      const { data } = await axios.post(`${API}/drafts`, {
        description,
        platforms,
        versions,
        selected_version: selectedVersion,
        image_path: imagePath
      })
      setSavedDraftId(data.id)
      showToast('Saved as draft', 'success')
      loadDrafts()
    } catch (e) {
      showToast('Failed to save', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handlePost = async (platform) => {
    if (!versions || !selectedVersion) {
      showToast('Select a version first', 'error')
      return
    }

    const PLATFORM_META = {
      li: { connKey: 'linkedin',  label: 'LinkedIn' },
      fb: { connKey: 'facebook',  label: 'Facebook' },
      ig: { connKey: 'instagram', label: 'Instagram' },
    }
    const { connKey, label } = PLATFORM_META[platform] || PLATFORM_META.li
    if (!connections[connKey]) {
      showToast(`Connect ${label} first`, 'error')
      return
    }

    // Save draft first if not saved
    let draftId = savedDraftId
    if (!draftId) {
      setSaving(true)
      try {
        const { data } = await axios.post(`${API}/drafts`, {
          description, platforms, versions,
          selected_version: selectedVersion,
          image_path: imagePath
        })
        draftId = data.id
        setSavedDraftId(draftId)
      } catch (e) {
        showToast('Failed to save draft before posting', 'error')
        setSaving(false)
        return
      }
      setSaving(false)
    }

    setPosting(true)
    try {
      const { data } = await axios.post(`${API}/post`, {
        post_id: draftId,
        platforms: [connKey]
      })
      if (data[connKey]?.success) {
        showToast(`Posted to ${label}!`, 'success')
        loadDrafts()
      } else {
        showToast(data[connKey]?.error || 'Post failed', 'error')
      }
    } catch (e) {
      showToast('Posting failed', 'error')
    } finally {
      setPosting(false)
    }
  }

  const selectedContent = versions && selectedVersion
    ? versions[selectedVersion]?.content
    : null

  return (
    <div className="app">
      {/* Topbar */}
      <header className="topbar">
        <div className="topbar-brand">
          <img
            src="/logo.avif"
            alt="Confiscore"
            style={{ height: 28, width: 'auto', filter: 'brightness(1)' }}
            onError={(e) => {
              e.target.style.display = 'none'
              e.target.nextSibling.style.display = 'flex'
            }}
          />
          <div className="topbar-logo" style={{ display: 'none' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="8" stroke="white" strokeWidth="2"/>
              <path d="M9 12.5l2 2 4-4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>
        <div className="topbar-right">
          <nav className="topbar-nav">
            <button
              className={`nav-btn ${view === 'compose' ? 'active' : ''}`}
              onClick={() => setView('compose')}
            >
              Compose
            </button>
            <button
              className={`nav-btn ${view === 'drafts' ? 'active' : ''}`}
              onClick={() => { setView('drafts'); loadDrafts() }}
            >
              Drafts & Posts
              {drafts.length > 0 && (
                <span style={{ marginLeft: 5, background: 'rgba(255,255,255,0.15)', borderRadius: 10, padding: '0 6px', fontSize: 10 }}>
                  {drafts.length}
                </span>
              )}
            </button>
          </nav>
          <Connections
            connections={connections}
            onConnect={loadConnections}
            compact
          />
        </div>
      </header>

      {/* Main */}
      <div className="main-content">
        {view === 'compose' ? (
          <>
            {/* Left: Composer */}
            <aside className="left-panel">
              <Composer
                description={description}
                setDescription={setDescription}
                platforms={platforms}
                setPlatforms={setPlatforms}
                onGenerate={handleGenerate}
                generating={generating}
                generationStep={generationStep}
              />
              <div style={{ padding: '0 1.25rem' }}>
                <div className="divider" />
              </div>
              <div className="panel-section">
                <div className="section-label">Image</div>
                <ImageUpload
                  imageUrl={imageUrl}
                  setImageUrl={setImageUrl}
                  setImagePath={setImagePath}
                  showToast={showToast}
                />
              </div>
              {versions && (
                <div className="panel-section" style={{ paddingBottom: '1.25rem' }}>
                  <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                    <button
                      className="btn btn-secondary"
                      style={{ flex: 1 }}
                      onClick={handleSaveDraft}
                      disabled={saving}
                    >
                      {saving ? <span className="spin" /> : '↓'} Save draft
                    </button>
                  </div>
                </div>
              )}
            </aside>

            {/* Right: Versions + Preview */}
            <div className="right-panel">
              <div className="tab-bar">
                <div className="tab active">
                  {versions ? '4 Versions' : 'Preview'}
                  {versions && <span className="tab-count">4</span>}
                </div>
              </div>

              <div className="tab-content">
                {generating ? (
                  <div className="loading-overlay">
                    <div className="loading-spinner" />
                    <div style={{ textAlign: 'center' }}>
                      <p style={{ fontWeight: 600, marginBottom: 12, color: 'var(--navy)' }}>
                        Generating 4 versions...
                      </p>
                      <div className="loading-steps">
                        {['Searching web for real data', 'Engineering content brief', 'Writing 4 versions'].map((step, i) => (
                          <span key={i} className={`loading-step ${generationStep > i ? 'done' : generationStep === i + 1 ? 'active' : ''}`}>
                            {generationStep > i ? '✓ ' : ''}{step}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : versions ? (
                  <>
                    <Versions
                      versions={versions}
                      selectedVersion={selectedVersion}
                      setSelectedVersion={setSelectedVersion}
                      platforms={platforms}
                    />
                    {selectedContent && (
                      <Preview
                        content={selectedContent}
                        platforms={platforms}
                        previewPlatform={previewPlatform}
                        setPreviewPlatform={setPreviewPlatform}
                        imageUrl={imageUrl}
                        setImageUrl={setImageUrl}
                        setImagePath={setImagePath}
                        showToast={showToast}
                        description={description}
                      />
                    )}
                  </>
                ) : (
                  <div className="empty-state">
                    <div className="empty-state-icon">✦</div>
                    <p>Describe your post and hit <strong>Generate</strong></p>
                    <p style={{ marginTop: 6, fontSize: 12 }}>
                      4 versions will appear — Himaan voice, Brand, Data-driven, Inspiring
                    </p>
                  </div>
                )}
              </div>

              {/* Post action bar */}
              {versions && selectedContent && (
                <div className="post-action-bar">
                  <div className="post-action-left">
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      Post as: <strong style={{ color: 'var(--navy)' }}>
                        {versions[selectedVersion]?.name}
                      </strong>
                    </span>
                  </div>
                  <div className="post-action-right">
                    {platforms.includes('li') && (
                      <button
                        className="btn-post-li"
                        onClick={() => handlePost('li')}
                        disabled={posting || !connections.linkedin}
                        title={!connections.linkedin ? 'Connect LinkedIn first' : ''}
                      >
                        {posting ? <span className="spin" style={{ borderTopColor: 'white' }} /> : 'in'}
                        {connections.linkedin ? 'Post to LinkedIn' : 'Connect LinkedIn'}
                      </button>
                    )}
                    {platforms.includes('fb') && (
                      <button
                        className="btn-post-li"
                        style={{ background: '#1877F2' }}
                        onClick={() => handlePost('fb')}
                        disabled={posting || !connections.facebook}
                        title={!connections.facebook ? 'Connect Facebook first' : ''}
                      >
                        {posting ? <span className="spin" style={{ borderTopColor: 'white' }} /> : 'f'}
                        {connections.facebook ? 'Post to Facebook' : 'Connect Facebook'}
                      </button>
                    )}
                    {platforms.includes('ig') && (
                      <button
                        className="btn-post-ig"
                        onClick={() => handlePost('ig')}
                        disabled={posting || !connections.instagram}
                        title={!connections.instagram ? 'Connect Instagram first' : ''}
                      >
                        {posting ? <span className="spin" style={{ borderTopColor: 'white' }} /> : '◎'}
                        {connections.instagram ? 'Post to Instagram' : 'Connect Instagram'}
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, overflow: 'auto', padding: '1.5rem' }}>
            <Drafts
              drafts={drafts}
              connections={connections}
              onRefresh={loadDrafts}
              showToast={showToast}
            />
          </div>
        )}
      </div>

      <Toast toasts={toasts} />
    </div>
  )
}
