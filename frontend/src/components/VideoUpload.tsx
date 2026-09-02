import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { uploadVideo } from '../api/client'

const ALLOWED = ['.mp4', '.mov', '.mkv']
const MAX_MB = 80

export default function VideoUpload() {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)

  function validate(file: File): string | null {
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
    if (!ALLOWED.includes(ext)) {
      return `Unsupported type. Use ${ALLOWED.join(', ')}`
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      return `File exceeds ${MAX_MB}MB limit`
    }
    return null
  }

  async function handleFile(file: File) {
    const err = validate(file)
    if (err) {
      setError(err)
      return
    }
    setError(null)
    setUploading(true)
    setProgress(0)
    try {
      const res = await uploadVideo(file, setProgress)
      navigate(`/jobs/${res.job_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
      setUploading(false)
    }
  }

  return (
    <section className="w-full max-w-xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          const file = e.dataTransfer.files?.[0]
          if (file) void handleFile(file)
        }}
        className={`relative border border-dashed rounded-sm px-8 py-16 text-center transition-colors ${
          dragging
            ? 'border-[var(--accent)] bg-[var(--surface)]'
            : 'border-[var(--border)] bg-[var(--bg-elevated)]/60'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mov,.mkv,video/mp4,video/quicktime,video/x-matroska"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void handleFile(file)
          }}
        />
        <p className="text-[var(--accent)] text-xs tracking-[0.25em] uppercase mb-4">
          Drop video
        </p>
        <h2 className="text-2xl mb-2">Upload a clip to summarize</h2>
        <p className="text-[var(--muted)] text-sm mb-8">
          MP4, MOV, or MKV · under 2 minutes · up to {MAX_MB}MB
          <br />
          <span className="text-[var(--accent)]">Typical turnaround: ~2–3 minutes</span>
        </p>
        <button
          type="button"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
          className="px-6 py-2.5 bg-[var(--accent)] text-[var(--bg)] font-medium hover:bg-[var(--accent-dim)] transition-colors disabled:opacity-50"
        >
          {uploading ? 'Uploading…' : 'Choose file'}
        </button>

        {uploading && (
          <div className="mt-8 mx-auto max-w-xs">
            <div className="h-1 bg-[var(--border)] overflow-hidden">
              <motion.div
                className="h-full bg-[var(--accent)]"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-[var(--muted)] mt-2">{progress}%</p>
          </div>
        )}
      </motion.div>

      {error && (
        <p className="mt-4 text-center text-[var(--danger)] text-sm" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}
