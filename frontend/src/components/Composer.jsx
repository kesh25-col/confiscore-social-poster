import { useState } from 'react'
import axios from 'axios'

const PLATFORM_STEPS = [
  'Searching web for real data',
  'Engineering content brief',
  'Writing 4 versions in parallel'
]

export default function Composer({
  description, setDescription,
  platforms, setPlatforms,
  onGenerate, generating, generationStep,
  showToast
}) {
  const [mode, setMode] = useState('write')   // 'write' | 'research'
  const [seed, setSeed] = useState('')
  const [researching, setResearching] = useState(false)
  const [ideas, setIdeas] = useState([])

  const togglePlatform = (p) => {
    setPlatforms(prev =>
      prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]
    )
  }

  // Seed mode: enrich a short topic into a full description from Google + competitors + site
  const enrichSeed = async () => {
    if (!seed.trim()) { showToast('Enter a topic to research', 'error'); return }
    setResearching(true)
    setIdeas([])
    try {
      const { data } = await axios.post('/api/research', {
        mode: 'seed', seed: seed.trim(), platforms
      })
      setDescription(data.description)
      const src = [data.web_used && 'web', data.competitors_used && 'competitors']
        .filter(Boolean).join(' + ')
      showToast(`✓ Description researched${src ? ` (${src})` : ''}`, 'success')
    } catch (e) {
      showToast(e.response?.data?.detail || 'Research failed', 'error')
    } finally {
      setResearching(false)
    }
  }

  // Autonomous mode: suggest several ready post ideas to pick from
  const suggestIdeas = async () => {
    setResearching(true)
    setIdeas([])
    try {
      const { data } = await axios.post('/api/research', {
        mode: 'auto', platforms
      })
      setIdeas(data.ideas || [])
      if (!data.ideas?.length) showToast('No ideas returned — try again', 'error')
    } catch (e) {
      showToast(e.response?.data?.detail || 'Idea generation failed', 'error')
    } finally {
      setResearching(false)
    }
  }

  const pickIdea = (idea) => {
    setDescription(idea.description)
    setIdeas([])
    showToast('Idea loaded — tweak it or generate', 'success')
  }

  return (
    <>
      <div className="panel-section" style={{ paddingTop: '1.25rem' }}>
        <div className="section-label">Compose Post</div>

        {/* Mode toggle: write yourself vs auto-research */}
        <div className="compose-mode-toggle">
          <button
            className={`mode-btn ${mode === 'write' ? 'active' : ''}`}
            onClick={() => setMode('write')}
          >
            ✍️ Write myself
          </button>
          <button
            className={`mode-btn ${mode === 'research' ? 'active' : ''}`}
            onClick={() => setMode('research')}
          >
            🔍 Auto-research
          </button>
        </div>

        {mode === 'research' && (
          <div className="research-box">
            <label style={{ marginTop: 4 }}>Topic / angle (optional)</label>
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                type="text"
                value={seed}
                onChange={e => setSeed(e.target.value)}
                placeholder="e.g. hiring confidence, employee retention"
                style={{ flex: 1 }}
                onKeyDown={e => e.key === 'Enter' && enrichSeed()}
              />
              <button
                className="btn btn-secondary btn-sm"
                onClick={enrichSeed}
                disabled={researching}
                style={{ whiteSpace: 'nowrap' }}
              >
                {researching ? <span className="spin" /> : '→'} Enrich
              </button>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '8px 0' }}>
              <div className="divider" style={{ flex: 1 }} />
              <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>OR</span>
              <div className="divider" style={{ flex: 1 }} />
            </div>
            <button
              className="btn btn-secondary"
              onClick={suggestIdeas}
              disabled={researching}
              style={{ width: '100%' }}
            >
              {researching ? <><span className="spin" /> Researching…</> : '✦ Suggest ideas for me'}
            </button>
            <p style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 6 }}>
              Pulls from Google, your competitors, and confiscore.com.
            </p>

            {ideas.length > 0 && (
              <div className="idea-list">
                {ideas.map((idea, i) => (
                  <div key={i} className="idea-card" onClick={() => pickIdea(idea)}>
                    <div className="idea-title">{idea.title}</div>
                    <div className="idea-desc">{idea.description}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <label style={{ marginTop: mode === 'research' ? 10 : 0 }}>
          {mode === 'research' ? 'Researched description (edit freely)' : 'What do you want to post about?'}
        </label>
        <textarea
          rows={5}
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="e.g. We just hit 500 users on Confiscore for Recruitment — want to share this milestone with a data angle"
          style={{ marginBottom: 0 }}
        />
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5 }}>
          Be specific — include the angle, audience, or key message you want.
        </p>
      </div>

      <div className="panel-section" style={{ marginTop: 4 }}>
        <div className="section-label">Platforms</div>
        <div className="platform-list">
          {[
            { key: 'li', label: 'LinkedIn', icon: 'in' },
            { key: 'fb', label: 'Facebook', icon: 'f' },
            { key: 'ig', label: 'Instagram', icon: 'IG' }
          ].map(({ key, label, icon }) => (
            <div
              key={key}
              className={`platform-toggle ${platforms.includes(key) ? `active-${key}` : ''}`}
              onClick={() => togglePlatform(key)}
            >
              <div className={`plat-icon plat-icon-${key}`}>{icon}</div>
              <span className="plat-name">{label}</span>
              <div className="plat-check">
                {platforms.includes(key) && '✓'}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel-section" style={{ marginTop: 8 }}>
        <button
          className="btn btn-primary"
          onClick={onGenerate}
          disabled={generating || !description.trim() || !platforms.length}
        >
          {generating
            ? <><span className="spin" /> Generating...</>
            : '✦ Generate 4 versions'
          }
        </button>
        {generating && (
          <div style={{ marginTop: 10 }}>
            {PLATFORM_STEPS.map((step, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '4px 0',
                  fontSize: 12,
                  color: generationStep > i + 1 ? 'var(--success)'
                    : generationStep === i + 1 ? 'var(--accent)'
                    : 'var(--text-muted)'
                }}
              >
                <span style={{ width: 14, textAlign: 'center' }}>
                  {generationStep > i + 1 ? '✓' : generationStep === i + 1 ? '●' : '○'}
                </span>
                {step}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
