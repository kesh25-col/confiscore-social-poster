import { useCallback, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'

export default function ImageUpload({ imageUrl, setImageUrl, setImagePath, showToast }) {
  const onDrop = useCallback(async (files) => {
    const file = files[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    try {
      const { data } = await axios.post('/api/upload-image', formData)
      setImageUrl(data.url)
      setImagePath(data.path)
      showToast('Image ready', 'success')
    } catch (err) {
      showToast('Upload failed — max 10MB', 'error')
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.gif', '.webp'] },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024
  })

  return (
    <div>
      {imageUrl ? (
        <div className="upload-preview">
          <img src={imageUrl} alt="Upload preview" />
          <button
            className="upload-preview-remove"
            onClick={() => { setImageUrl(null); setImagePath(null) }}
            title="Remove image"
          >
            ✕
          </button>
        </div>
      ) : (
        <div
          {...getRootProps()}
          className={`upload-zone ${isDragActive ? 'dragover' : ''}`}
        >
          <input {...getInputProps()} />
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ opacity: 0.4 }}>
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <circle cx="8.5" cy="8.5" r="1.5"/>
            <path d="M21 15l-5-5L5 21"/>
          </svg>
          <p>{isDragActive ? 'Drop it here' : 'Drag image here or click to upload'}</p>
          <p style={{ fontSize: 11 }}>JPG, PNG, GIF · max 10MB</p>
        </div>
      )}

      <div style={{ marginTop: 8 }}>
        <button
          className="btn btn-sm"
          style={{ width: '100%', justifyContent: 'center', opacity: 0.6 }}
          onClick={() => showToast('Add CANVA_CLIENT_ID to .env to enable Canva', 'info')}
        >
          🎨 Open in Canva
        </button>
        <p style={{ fontSize: 10.5, color: 'var(--text-muted)', textAlign: 'center', marginTop: 4 }}>
          Design with your brand templates
        </p>
      </div>
    </div>
  )
}
