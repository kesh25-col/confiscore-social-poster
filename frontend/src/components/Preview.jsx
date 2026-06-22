import { useRef, useState, useEffect } from 'react'
import axios from 'axios'

// Rasterize an SVG data URL to a PNG Blob in the browser (no native libs needed).
// LinkedIn/Meta only accept raster images, so generated SVG posters must be converted.
async function rasterizeSvgToPng(svgDataUrl) {
  const img = new Image()
  await new Promise((resolve, reject) => {
    img.onload = resolve
    img.onerror = () => reject(new Error('Could not load SVG for rasterization'))
    img.src = svgDataUrl
  })
  const w = img.naturalWidth || 1200
  const h = img.naturalHeight || 627
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  ctx.drawImage(img, 0, 0, w, h)
  return await new Promise((resolve, reject) =>
    canvas.toBlob(b => (b ? resolve(b) : reject(new Error('Canvas toBlob failed'))), 'image/png')
  )
}

function extractHashtags(text) {
  return (text.match(/#\w+/g) || []).join(' ')
}
function stripHashtags(text) {
  return text.replace(/#\w+/g, '').trim().replace(/\s{2,}/g, ' ')
}

function LinkedInMock({ text, imageUrl, onImageClick }) {
  return (
    <div className="li-mock">
      <div className="li-mock-card">
        <div className="li-mock-header">
          <div className="li-mock-avatar">DC</div>
          <div>
            <div className="li-mock-name">Dr. Debasis Chatterji</div>
            <div className="li-mock-title">Founder & CEO @Confiscore · 3rd+</div>
            <div className="li-mock-time">Just now · 🌐</div>
          </div>
        </div>
        <div className="li-mock-body">{text || ''}</div>
        {imageUrl ? (
          <div style={{ cursor: 'pointer' }} onClick={onImageClick}>
            <img src={imageUrl} alt="Post visual" style={{ width: '100%', display: 'block' }} />
          </div>
        ) : (
          <div className="li-mock-image-placeholder" onClick={onImageClick}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <path d="M21 15l-5-5L5 21"/>
            </svg>
            <span>Click to add image</span>
          </div>
        )}
        <div className="li-mock-actions">
          {['👍 Like', '💬 Comment', '↩ Repost', '➤ Send'].map(a => (
            <button key={a} className="li-action-btn">{a}</button>
          ))}
        </div>
      </div>
    </div>
  )
}

function FacebookMock({ text, imageUrl, onImageClick }) {
  return (
    <div className="li-mock">
      <div className="li-mock-card">
        <div className="li-mock-header">
          <div className="li-mock-avatar" style={{ background: '#1877F2' }}>CS</div>
          <div>
            <div className="li-mock-name">Confiscore</div>
            <div className="li-mock-title">Sponsored · Confidence Management</div>
            <div className="li-mock-time">Just now · 🌐</div>
          </div>
        </div>
        <div className="li-mock-body">{text || ''}</div>
        {imageUrl ? (
          <div style={{ cursor: 'pointer' }} onClick={onImageClick}>
            <img src={imageUrl} alt="Post visual" style={{ width: '100%', display: 'block' }} />
          </div>
        ) : (
          <div className="li-mock-image-placeholder" onClick={onImageClick}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <path d="M21 15l-5-5L5 21"/>
            </svg>
            <span>Click to add image</span>
          </div>
        )}
        <div className="li-mock-actions">
          {['👍 Like', '💬 Comment', '↪ Share'].map(a => (
            <button key={a} className="li-action-btn">{a}</button>
          ))}
        </div>
      </div>
    </div>
  )
}

function InstagramMock({ text, imageUrl, onImageClick }) {
  const tags = extractHashtags(text || '')
  const caption = stripHashtags(text || '')
  return (
    <div className="ig-mock">
      <div className="ig-mock-card">
        <div className="ig-mock-header">
          <div className="ig-mock-avatar">CS</div>
          <div className="ig-mock-username">confiscore</div>
        </div>
        <div className={`ig-mock-image ${!imageUrl ? 'empty' : ''}`} onClick={onImageClick}>
          {imageUrl ? (
            <img src={imageUrl} alt="Post visual" />
          ) : (
            <>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <path d="M21 15l-5-5L5 21"/>
              </svg>
              <span>Click to add image</span>
            </>
          )}
        </div>
        <div className="ig-mock-actions">
          <svg viewBox="0 0 24 24" strokeWidth="1.5"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
          <svg viewBox="0 0 24 24" strokeWidth="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <svg viewBox="0 0 24 24" strokeWidth="1.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </div>
        <div className="ig-mock-likes">128 likes</div>
        <div className="ig-mock-caption"><strong>confiscore </strong>{caption}</div>
        {tags && <div className="ig-mock-hashtags">{tags}</div>}
      </div>
    </div>
  )
}

export default function Preview({
  content, platforms, previewPlatform, setPreviewPlatform,
  imageUrl, setImageUrl, setImagePath, showToast,
  description
}) {
  const fileInputRef = useRef()
  const [aiUrl, setAiUrl] = useState(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiModel, setAiModel] = useState(null)
  const [aiFormat, setAiFormat] = useState('single')   // 'single' | 'carousel'
  const [aiImagePath, setAiImagePath] = useState(null) // server path to rasterized PNG

  // Carousel is LinkedIn-only — fall back to single poster on Instagram
  useEffect(() => {
    if (previewPlatform !== 'li' && aiFormat === 'carousel') {
      setAiFormat('single')
    }
  }, [previewPlatform, aiFormat])

  const handleImageClick = () => fileInputRef.current?.click()

  const handleFileChange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    try {
      const { data } = await axios.post('/api/upload-image', formData)
      setImageUrl(data.url)
      setImagePath(data.path)
      setShowPoster(false)
      showToast('Image uploaded', 'success')
    } catch {
      showToast('Upload failed', 'error')
    }
    e.target.value = ''
  }

  const generateAIPoster = async () => {
    const postText = content?.[previewPlatform] || ''
    if (!postText) { showToast('Select a version first', 'error'); return }
    setAiLoading(true)
    try {
      const { data } = await axios.post('/api/poster/ai', {
        description,
        platform: previewPlatform,
        post_text: postText,   // the SELECTED voice drives the poster
        format: aiFormat
      })
      setAiUrl(data.image)
      setAiModel(data.model)
      setImageUrl(data.image)   // SVG renders crisply in the preview

      // Rasterize the SVG to a PNG and upload it, so it can be posted (LinkedIn needs raster).
      try {
        const pngBlob = await rasterizeSvgToPng(data.image)
        const fd = new FormData()
        fd.append('file', pngBlob, 'poster.png')
        const up = await axios.post('/api/upload-image', fd)
        setAiImagePath(up.data.path)
        setImagePath(up.data.path)
      } catch (convErr) {
        console.error('Poster rasterization failed:', convErr)
        setAiImagePath(null)
        setImagePath(null)
        showToast('Poster ready, but image could not be prepared for posting', 'error')
      }

      showToast(aiFormat === 'carousel' ? '✦ Carousel ready' : '✦ AI poster ready', 'success')
    } catch (e) {
      showToast(e.response?.data?.detail || 'AI generation failed', 'error')
    } finally {
      setAiLoading(false)
    }
  }

const text = content?.[previewPlatform] || content?.[platforms[0]] || ''
  const displayImage = imageUrl

  return (
    <>
      <div className="preview-section">
        <div className="preview-header">
          <span className="preview-title">Platform Preview</span>
          <div className="platform-tabs">
            {platforms.map(p => (
              <button
                key={p}
                className={`plat-tab ${p} ${previewPlatform === p ? 'active' : ''}`}
                onClick={() => setPreviewPlatform(p)}
              >
                {p === 'li' ? 'LinkedIn' : p === 'fb' ? 'Facebook' : 'Instagram'}
              </button>
            ))}
          </div>
        </div>

        <input ref={fileInputRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFileChange} />

        {previewPlatform === 'li'
          ? <LinkedInMock text={text} imageUrl={displayImage} onImageClick={handleImageClick} />
          : previewPlatform === 'fb'
          ? <FacebookMock text={text} imageUrl={displayImage} onImageClick={handleImageClick} />
          : <InstagramMock text={text} imageUrl={displayImage} onImageClick={handleImageClick} />
        }
      </div>

      {/* AI Poster generator */}
      <div className="poster-section" style={{ marginTop: '1rem' }}>
        <div className="poster-header">
          <span className="poster-title">AI Image Generation</span>
          <span style={{ fontSize: 11, color: 'var(--white-muted)', fontFamily: 'var(--font-body)' }}>
            Claude · SVG
          </span>
        </div>

        {/* Format selector: single poster vs carousel (carousel = LinkedIn only) */}
        <div style={{ display: 'flex', gap: 8, padding: '12px 16px 0' }}>
          {[
            { key: 'single', label: '▢ Single poster' },
            ...(previewPlatform === 'li' ? [{ key: 'carousel', label: '▦ Carousel' }] : []),
          ].map(opt => (
            <button
              key={opt.key}
              onClick={() => setAiFormat(opt.key)}
              disabled={aiLoading}
              style={{
                flex: 1,
                fontSize: 12.5,
                fontWeight: 600,
                padding: '8px 10px',
                borderRadius: 999,
                cursor: aiLoading ? 'default' : 'pointer',
                border: '1px solid',
                borderColor: aiFormat === opt.key ? 'var(--accent)' : 'var(--border2)',
                background: aiFormat === opt.key ? 'var(--accent-soft)' : 'var(--bg2)',
                color: aiFormat === opt.key ? 'var(--accent)' : 'var(--white-muted)',
                fontFamily: 'var(--font-body)',
                transition: 'all 0.15s',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="poster-btn-row" style={{ paddingTop: 12 }}>
          <button
            className={`btn-poster ${aiUrl && !aiLoading ? 'active' : ''}`}
            onClick={generateAIPoster}
            disabled={aiLoading}
          >
            {aiLoading
              ? '⟳ generating...'
              : aiFormat === 'carousel' ? '✦ Generate carousel' : '✦ Generate poster'}
          </button>
          {aiUrl && (
            <button
              className="btn-poster"
              onClick={() => {
                setAiUrl(null)
                setImageUrl(null); setImagePath(null)
              }}
            >
              ✕ clear
            </button>
          )}
        </div>
        {aiLoading && (
          <div className="poster-placeholder">
            <span style={{ color: 'var(--accent)', fontSize: 13, fontWeight: 550 }}>
              ⟳ {aiFormat === 'carousel'
                ? 'Building carousel slides — this takes 20–40 seconds...'
                : 'Designing poster — this takes 10–20 seconds...'}
            </span>
          </div>
        )}
        {!aiUrl && !aiLoading && (
          <div className="poster-placeholder">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ opacity: 0.3 }}>
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M3 9h18M9 21V9"/>
            </svg>
            <span>Claude designs a real poster or carousel in SVG from your content</span>
          </div>
        )}
        {aiUrl && !aiLoading && (
          <div className="poster-img-wrap">
            <div style={{ fontSize: 11, color: 'var(--white-muted)', marginBottom: 8, fontFamily: 'var(--font-body)' }}>
              ✦ Claude SVG · {aiFormat === 'carousel' ? 'carousel (scroll to view slides)' : 'click image to use as post visual'}
            </div>
            <img src={aiUrl} alt="AI generated visual" style={{ cursor: 'pointer', width: '100%' }}
              onClick={() => { setImageUrl(aiUrl); setImagePath(aiImagePath) }} />
          </div>
        )}
      </div>
    </>
  )
}
