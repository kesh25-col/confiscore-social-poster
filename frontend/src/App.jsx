import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import Composer from './components/Composer'
import Versions from './components/Versions'
import Preview from './components/Preview'
import ImageUpload from './components/ImageUpload'
import Connections from './components/Connections'
import Drafts from './components/Drafts'
import Calendar from './components/Calendar'
import Settings from './components/Settings'
import Login from './components/Login'
import Toast from './components/Toast'

const API = '/api'

export default function App() {
  const [view, setView] = useState('compose') // compose | calendar | drafts | settings
  const [scheduleAt, setScheduleAt] = useState('')
  const [scheduling, setScheduling] = useState(false)
  const [authState, setAuthState] = useState('loading') // loading | locked | open
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

  // Decide whether a login gate is needed, then load data
  useEffect(() => {
    // If any request comes back 401, the token is missing/stale — show login.
    const interceptor = axios.interceptors.response.use(
      r => r,
      err => {
        if (err.response?.status === 401) {
          localStorage.removeItem('cs_auth')
          delete axios.defaults.headers.common['X-Auth-Token']
          setAuthState('locked')
        }
        return Promise.reject(err)
      }
    )

    ;(async () => {
      try {
        const { data } = await axios.get(`${API}/auth-required`)
        if (data.required && !localStorage.getItem('cs_auth')) {
          setAuthState('locked')
          return
        }
      } catch { /* if probe fails, fall through and let requests decide */ }
      setAuthState('open')
      initData()
    })()

    return () => axios.interceptors.response.eject(interceptor)
  }, [])

  // Initial data load + OAuth return handling (runs once the gate is open)
  const initData = () => {
    loadConnections()
    loadDrafts()
    const params = new URLSearchParams(window.location.search)
    const connected = params.get('connected')
    if (connected) {
      // May be comma-separated e.g. "facebook,instagram"
      const platforms = connected.split(',')
      const label = platforms.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(' & ')
      showToast(`${label} connected successfully!`, 'success')
      window.history.replaceState({}, '', window.location.pathname)
      loadConnections()
    }
  }

  const handleLoginSuccess = () => {
    setAuthState('open')
    initData()
  }

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

  const handleSchedule = async () => {
    if (!versions) { showToast('Generate a post first', 'error'); return }
    if (!selectedVersion) { showToast('Select a version first', 'error'); return }
    if (!scheduleAt) { showToast('Pick a date & time', 'error'); return }
    const when = new Date(scheduleAt)
    if (isNaN(when) || when < new Date()) { showToast('Pick a future date & time', 'error'); return }

    setScheduling(true)
    try {
      if (savedDraftId) {
        await axios.patch(`${API}/drafts/${savedDraftId}`, {
          selected_version: selectedVersion,
          image_path: imagePath,
          scheduled_for: when.toISOString(),
        })
      } else {
        const { data } = await axios.post(`${API}/drafts`, {
          description, platforms, versions,
          selected_version: selectedVersion,
          image_path: imagePath,
          scheduled_for: when.toISOString(),
        })
        setSavedDraftId(data.id)
      }
      showToast(`Scheduled for ${when.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}`, 'success')
      setScheduleAt('')
      loadDrafts()
      setView('calendar')
    } catch (e) {
      showToast('Failed to schedule', 'error')
    } finally {
      setScheduling(false)
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

    // Instagram requires an image
    if (platform === 'ig' && !imagePath) {
      showToast('Instagram requires an image — please add one before posting', 'error')
      return
    }

    // Save or sync draft so DB always has the latest imagePath + selectedVersion
    let draftId = savedDraftId
    setSaving(true)
    try {
      if (!draftId) {
        const { data } = await axios.post(`${API}/drafts`, {
          description, platforms, versions,
          selected_version: selectedVersion,
          image_path: imagePath
        })
        draftId = data.id
        setSavedDraftId(draftId)
      } else {
        // Push any image or voice changes made after the draft was first saved
        await axios.patch(`${API}/drafts/${draftId}`, {
          selected_version: selectedVersion,
          ...(imagePath ? { image_path: imagePath } : {})
        })
      }
    } catch (e) {
      showToast('Failed to save draft before posting', 'error')
      setSaving(false)
      return
    }
    setSaving(false)

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

  const handleOpenDraft = (draft) => {
    setDescription(draft.description)
    setPlatforms(draft.platforms || ['li'])
    setVersions(draft.versions)
    setSelectedVersion(draft.selected_version || Object.keys(draft.versions || {})[0])
    setPreviewPlatform((draft.platforms || ['li'])[0])
    setSavedDraftId(draft.id)
    if (draft.image_path) {
      setImageUrl(`/uploads/${draft.image_path}`)
      setImagePath(draft.image_path)
    } else {
      setImageUrl(null)
      setImagePath(null)
    }
    setView('compose')
    showToast('Draft loaded', 'success')
  }

  const selectedContent = versions && selectedVersion
    ? versions[selectedVersion]?.content
    : null

  // Gate: while probing, show a minimal splash; if locked, show login.
  if (authState === 'loading') {
    return (
      <div className="login-screen">
        <div className="loading-spinner" />
      </div>
    )
  }
  if (authState === 'locked') {
    return <Login onSuccess={handleLoginSuccess} />
  }

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
              className={`nav-btn ${view === 'calendar' ? 'active' : ''}`}
              onClick={() => { setView('calendar'); loadDrafts() }}
            >
              Calendar
            </button>
            <button
              className={`nav-btn ${view === 'drafts' ? 'active' : ''}`}
              onClick={() => { setView('drafts'); loadDrafts() }}
            >
              Drafts & Posts
              {drafts.length > 0 && (
                <span style={{ marginLeft: 6, background: 'var(--accent-soft)', color: 'var(--accent)', borderRadius: 999, padding: '1px 8px', fontSize: 11, fontWeight: 700 }}>
                  {drafts.length}
                </span>
              )}
            </button>
            <button
              className={`nav-btn ${view === 'settings' ? 'active' : ''}`}
              onClick={() => setView('settings')}
            >
              Settings
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
                showToast={showToast}
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

                  <div className="divider" />
                  <div className="section-label">Schedule</div>
                  <input
                    type="datetime-local"
                    value={scheduleAt}
                    onChange={e => setScheduleAt(e.target.value)}
                    min={new Date().toISOString().slice(0, 16)}
                    style={{ marginBottom: 8 }}
                  />
                  <button
                    className="btn btn-secondary"
                    style={{ width: '100%' }}
                    onClick={handleSchedule}
                    disabled={scheduling || !scheduleAt}
                  >
                    {scheduling ? <span className="spin" /> : '🗓️'} Schedule post
                  </button>
                  <p style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 6 }}>
                    Appears on the Calendar. You publish it with one click when it's due.
                  </p>
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
                        voiceKey={selectedVersion}
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
        ) : view === 'calendar' ? (
          <div style={{ flex: 1, overflow: 'auto', padding: '1.5rem' }}>
            <Calendar
              drafts={drafts}
              connections={connections}
              onRefresh={loadDrafts}
              showToast={showToast}
              onOpen={handleOpenDraft}
            />
          </div>
        ) : view === 'settings' ? (
          <div style={{ flex: 1, overflow: 'auto', padding: '1.5rem' }}>
            <Settings
              connections={connections}
              onConnect={loadConnections}
              showToast={showToast}
            />
          </div>
        ) : (
          <div style={{ flex: 1, overflow: 'auto', padding: '1.5rem' }}>
            <Drafts
              drafts={drafts}
              connections={connections}
              onRefresh={loadDrafts}
              showToast={showToast}
              onOpen={handleOpenDraft}
            />
          </div>
        )}
      </div>

      <Toast toasts={toasts} />
    </div>
  )
}
