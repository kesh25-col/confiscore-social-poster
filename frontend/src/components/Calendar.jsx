import { useState } from 'react'
import axios from 'axios'

const PLATFORM_NAMES = { li: 'LinkedIn', fb: 'Facebook', ig: 'Instagram' }
const PLATFORM_CONN = { li: 'linkedin', fb: 'facebook', ig: 'instagram' }
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December']
const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

// Local YYYY-MM-DD key for a date
function dayKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function Calendar({ drafts, connections, onRefresh, showToast, onOpen }) {
  const [cursor, setCursor] = useState(() => { const d = new Date(); d.setDate(1); return d })
  const [selectedDay, setSelectedDay] = useState(null)
  const [posting, setPosting] = useState(null)

  // Only posts that have a scheduled_for date
  const scheduled = drafts.filter(d => d.scheduled_for)
  const byDay = {}
  for (const p of scheduled) {
    const k = dayKey(new Date(p.scheduled_for))
    ;(byDay[k] ||= []).push(p)
  }

  const year = cursor.getFullYear()
  const month = cursor.getMonth()
  const firstDow = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const todayKey = dayKey(new Date())
  const now = new Date()

  const cells = []
  for (let i = 0; i < firstDow; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d))

  const handlePost = async (post) => {
    if (!post.selected_version) { showToast('Open the post and pick a version first', 'error'); return }
    const connKeys = (post.platforms || []).map(p => PLATFORM_CONN[p]).filter(Boolean)
    const connected = connKeys.filter(k => connections[k])
    if (!connected.length) { showToast('Connect a platform first', 'error'); return }

    setPosting(post.id)
    try {
      const { data } = await axios.post('/api/post', { post_id: post.id, platforms: connected })
      const ok = Object.values(data).some(r => r.success)
      if (ok) { showToast('Posted!', 'success'); onRefresh() }
      else {
        const err = Object.values(data).find(r => !r.success)?.error || 'Post failed'
        showToast(err, 'error')
      }
    } catch (e) {
      showToast('Posting failed', 'error')
    } finally {
      setPosting(null)
    }
  }

  const unschedule = async (post) => {
    try {
      await axios.patch(`/api/drafts/${post.id}`, { scheduled_for: '' })
      showToast('Removed from calendar', 'info')
      onRefresh()
    } catch { showToast('Failed', 'error') }
  }

  const selectedPosts = selectedDay ? (byDay[selectedDay] || []) : []

  return (
    <div className="calendar-wrap">
      <div className="calendar-main">
        <div className="cal-header">
          <h2 style={{ fontSize: 18 }}>{MONTHS[month]} {year}</h2>
          <div className="cal-nav">
            <button className="btn btn-sm" onClick={() => setCursor(new Date(year, month - 1, 1))}>‹</button>
            <button className="btn btn-sm" onClick={() => { const d = new Date(); d.setDate(1); setCursor(d) }}>Today</button>
            <button className="btn btn-sm" onClick={() => setCursor(new Date(year, month + 1, 1))}>›</button>
          </div>
        </div>

        <div className="cal-grid cal-dow">
          {DOW.map(d => <div key={d} className="cal-dow-cell">{d}</div>)}
        </div>
        <div className="cal-grid">
          {cells.map((d, i) => {
            if (!d) return <div key={i} className="cal-cell empty" />
            const k = dayKey(d)
            const posts = byDay[k] || []
            const isToday = k === todayKey
            const isSelected = k === selectedDay
            return (
              <div
                key={i}
                className={`cal-cell ${isToday ? 'today' : ''} ${isSelected ? 'selected' : ''} ${posts.length ? 'has-posts' : ''}`}
                onClick={() => setSelectedDay(k)}
              >
                <span className="cal-daynum">{d.getDate()}</span>
                <div className="cal-chips">
                  {posts.slice(0, 3).map(p => {
                    const due = new Date(p.scheduled_for) <= now && p.status !== 'published'
                    const published = p.status === 'published'
                    return (
                      <div
                        key={p.id}
                        className={`cal-chip ${published ? 'published' : due ? 'due' : ''}`}
                        title={p.description}
                      >
                        {published ? '✓ ' : due ? '● ' : ''}{p.description.slice(0, 18)}
                      </div>
                    )
                  })}
                  {posts.length > 3 && <div className="cal-chip more">+{posts.length - 3} more</div>}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Side panel for the selected day */}
      <div className="cal-side">
        {selectedDay ? (
          <>
            <div className="cal-side-head">
              {new Date(selectedDay + 'T00:00').toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}
            </div>
            {selectedPosts.length === 0 ? (
              <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 10 }}>
                Nothing scheduled. Schedule a post from Compose.
              </p>
            ) : (
              selectedPosts.map(p => {
                const time = new Date(p.scheduled_for).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
                const due = new Date(p.scheduled_for) <= now && p.status !== 'published'
                const published = p.status === 'published'
                return (
                  <div key={p.id} className="cal-side-card">
                    <div className="cal-side-time">
                      {time}
                      <span className={`status-badge status-${published ? 'published' : due ? 'scheduled' : 'draft'}`}>
                        {published ? 'published' : due ? 'due now' : 'scheduled'}
                      </span>
                    </div>
                    <div className="cal-side-desc">{p.description}</div>
                    <div className="draft-platforms" style={{ marginTop: 6 }}>
                      {p.platforms?.map(pl => (
                        <span key={pl} className={`plat-pill ${pl}`}>{PLATFORM_NAMES[pl]}</span>
                      ))}
                    </div>
                    <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
                      <button className="btn btn-sm" onClick={() => onOpen(p)}>↗ Open</button>
                      {!published && (
                        <button
                          className="btn btn-primary btn-sm"
                          style={{ width: 'auto', padding: '6px 14px' }}
                          onClick={() => handlePost(p)}
                          disabled={posting === p.id}
                        >
                          {posting === p.id ? <span className="spin" /> : '➤'} Post now
                        </button>
                      )}
                      {!published && (
                        <button className="btn btn-danger btn-sm" onClick={() => unschedule(p)}>✕</button>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </>
        ) : (
          <div className="cal-side-empty">
            <div style={{ fontSize: 28, marginBottom: 8 }}>🗓️</div>
            <p style={{ fontSize: 13 }}>Click a day to see what's scheduled.</p>
            <p style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 8 }}>
              <span style={{ color: 'var(--accent)' }}>●</span> due &nbsp;
              <span style={{ color: 'var(--success)' }}>✓</span> published
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
