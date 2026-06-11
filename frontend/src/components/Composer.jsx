const PLATFORM_STEPS = [
  'Searching web for real data',
  'Engineering content brief',
  'Writing 4 versions in parallel'
]

export default function Composer({
  description, setDescription,
  platforms, setPlatforms,
  onGenerate, generating, generationStep
}) {
  const togglePlatform = (p) => {
    setPlatforms(prev =>
      prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]
    )
  }

  return (
    <>
      <div className="panel-section" style={{ paddingTop: '1.25rem' }}>
        <div className="section-label">Compose Post</div>
        <label>What do you want to post about?</label>
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
